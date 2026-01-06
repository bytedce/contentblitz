# agents.py
import os
import json
import requests
from datetime import datetime
import token
from huggingface_hub import InferenceClient
from logging import log
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from config import LLM_MODEL, OPENROUTER_API_KEY, HF_IMAGE_MODEL, HF_API_TOKEN, LINKEDIN_ACCESS_TOKEN, LINKEDIN_USER_ID, LINKEDIN_UGC_URL
from rag import run_rag
from tools import tavily_search_with_content


# --------------------------------------------------
# Research Agent
# --------------------------------------------------

class ResearchAgent:
    def run(self, topic, log):
        log("RESEARCH", "ResearchAgent started")

        log("RESEARCH", "Running internal product RAG")
        catalog_research = run_rag(topic, log)

        log("RESEARCH", "Fetching Tavily cached web intelligence")
        web_results = tavily_search_with_content(topic)

        web_context = []
        for item in web_results[:3]:
            log("RESEARCH", f"Using Tavily data from: {item['url']}")
            web_context.append(item["content"])

        combined_web = "\n\n".join(web_context)

        log("RESEARCH", "Synthesizing research output")
        llm = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.3,
        )

        prompt = ChatPromptTemplate.from_template(
            """
            You are a senior beauty product marketing analyst.

            INTERNAL PRODUCT CATALOG (SOURCE OF TRUTH):
            {catalog}

            EXTERNAL MARKET INTELLIGENCE:
            {web}

            TASK:
            1. Select best-matching catalog products
            2. Add competitive positioning (non-medical)
            3. Highlight pricing and rating advantages
            4. Produce a structured research brief for blog creation

            TOPIC:
            {topic}
            """
        )

        # First format the prompt
        prompt_value = prompt.invoke(
            {
                "catalog": catalog_research,
                "web": combined_web,
                "topic": topic,
            }
        )

        # Then send it to the LLM
        final_research = llm.invoke(prompt_value).content

        log("RESEARCH", "Research synthesis completed")
        return final_research


# --------------------------------------------------
# Blog Writer Agent
# --------------------------------------------------

class BlogWriterAgent:
    def run(self, research, topic, log):
        log("BLOG", "BlogWriterAgent started")
        log("BLOG", "Drafting marketing blog")

        llm = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.3,
        )

        prompt = ChatPromptTemplate.from_template(
            """
            You are a professional beauty brand content strategist.

            RESEARCH INPUT:
            {research}

            TOPIC:
            {topic}

            BLOG REQUIREMENTS:
            - SEO-friendly headings
            - Consumer-centric benefits
            - Pricing/rating mentions where applicable
            - No medical or ingredient claims
            - Premium but friendly tone

            STRUCTURE:
            1. Engaging introduction
            2. Product-focused sections
            3. Why customers prefer these options
            4. Buying considerations
            5. Soft CTA

            Insert exactly 3–4 image placeholders like:
            [IMAGE: short descriptive caption]
            """
        )


        # First format the prompt
        prompt_value = prompt.invoke(
            {
                "research": research,
                "topic": topic,
            }
        )

        blog = llm.invoke(prompt_value).content

        log("BLOG", "Blog generation completed")
        return blog


# --------------------------------------------------
# Image Prompt Agent
# --------------------------------------------------

# agents.py (ImageGeneratorAgent)

class ImageGeneratorAgent:
    def __init__(self):
        self.client = InferenceClient(api_key=HF_API_TOKEN)
        self.model = HF_IMAGE_MODEL

    def run(self, blog: str, emit_event):
        emit_event("IMAGE", "ImageGeneratorAgent started")
        emit_event("IMAGE", "Generating single best marketing image prompt")

        # -----------------------------
        # 1. Generate ONE image prompt
        # -----------------------------
        llm = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.3,
        )

        prompt = ChatPromptTemplate.from_template(
            """
            You are a marketing image prompt specialist.

            From the blog below, generate ONE single best
            high-conversion marketing image idea.

            BLOG:
            {blog}

            RULES:
            - Generate ONLY ONE image
            - Image should look premium and realistic
            - Suitable for beauty / cosmetic marketing
            - Clean background, studio lighting

            OUTPUT JSON ONLY:
            {{
            "caption": "...",
            "prompt": "..."
            }}
            """
        )

        prompt_value = prompt.invoke({"blog": blog})
        image_prompt_json = llm.invoke(prompt_value).content

        try:
            image_prompt = json.loads(image_prompt_json)
        except json.JSONDecodeError:
            raise ValueError("Failed to parse image prompt JSON")

        emit_event("IMAGE", "Image prompt generated successfully")

        # -----------------------------
        # 2. Generate image via HF
        # -----------------------------
        emit_event("IMAGE", "Generating image using Hugging Face FLUX model")

        image = self.client.text_to_image(
            image_prompt["prompt"],
            model=self.model,
        )

        # -----------------------------
        # 3. Save image
        # -----------------------------
        os.makedirs("generated_images", exist_ok=True)

        filename = f"blog_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join("generated_images", filename)

        image.save(filepath)

        emit_event("IMAGE", f"Image generated and saved at {filepath}")
        emit_event("IMAGE", "ImageGeneratorAgent completed")

        # -----------------------------
        # 4. Return structured result
        # -----------------------------
        return {
            "caption": image_prompt["caption"],
            "prompt": image_prompt["prompt"],
            "image_path": filepath,
            "model": self.model,
        }


# --------------------------------------------------
# LinkedIn Post Agent
# --------------------------------------------------

class LinkedInPostAgent:
    def run(self, blog, log):
        log("LINKEDIN", "LinkedInPostAgent started")
        log("LINKEDIN", "Generating LinkedIn marketing post")

        llm = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.3,
        )

        prompt = ChatPromptTemplate.from_template(
            """
            Create a high-engagement LinkedIn post from the blog below.

            BLOG:
            {blog}

            RULES:
            - Strong opening hook
            - Emojis used naturally (✨🔥💄🛍️)
            - Short paragraphs
            - Max 4 hashtags
            - Under 1300 characters
            - Brand-safe, no medical claims

            Return ONLY the post text.
            """
        )

        prompt_value = prompt.invoke(
            {
                "blog": blog,
            }
        )

        post = llm.invoke(prompt_value).content

        log("LINKEDIN", "LinkedIn post generation completed")
        return post

class LinkedInPostSubmitAgent:
    """
    Posts content to a PERSONAL LinkedIn profile using an existing access token.
    """

    def __init__(self, access_token: str = None, user_id: str = None):
        self.access_token = LINKEDIN_ACCESS_TOKEN
        self.user_id = LINKEDIN_USER_ID

        if not self.access_token:
            raise EnvironmentError("LinkedIn access token not provided")

        if not self.user_id:
            raise EnvironmentError("LinkedIn user_id (sub) not provided")

    def post(self, text: str, emit_event):
        emit_event("LINKEDIN", "Preparing LinkedIn personal post")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        payload = {
            "author": f"urn:li:person:{self.user_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        }

        emit_event("LINKEDIN", "Sending post to LinkedIn")

        response = requests.post(
            LINKEDIN_UGC_URL,
            headers=headers,
            json=payload,
            timeout=15,
        )

        if response.status_code not in (200, 201):
            emit_event(
                "ERROR",
                f"LinkedIn API error {response.status_code}: {response.text}",
            )
            raise RuntimeError("Failed to post on LinkedIn")

        emit_event("LINKEDIN", "Post successfully published on LinkedIn")

        return response.json()

# --------------------------------------------------
# Orchestrator
# --------------------------------------------------

class ContentOrchestrator:
    def __init__(self):
        self.research_agent = ResearchAgent()
        self.blog_agent = BlogWriterAgent()
        self.image_agent = ImageGeneratorAgent()
        self.linkedin_agent = LinkedInPostAgent()

    def run(self, topic, log):
        log("SYSTEM", "Dispatching ResearchAgent")
        research = self.research_agent.run(topic, log)

        log("SYSTEM", "Dispatching BlogWriterAgent")
        blog = self.blog_agent.run(research, topic, log)

        log("SYSTEM", "Dispatching ImageGeneratorAgent")
        images = self.image_agent.run(blog, log)

        log("SYSTEM", "Dispatching LinkedInPostAgent")
        linkedin = self.linkedin_agent.run(blog, log)

        log("SYSTEM", "All agents completed")


        return {
            "topic": topic,
            "research": research,
            "blog": blog,
            "images": images,
            "linkedin": linkedin,
        }
