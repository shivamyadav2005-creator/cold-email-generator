import os
import uuid
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from dotenv import load_dotenv

load_dotenv()


class Chain:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        model_name = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        if api_key and api_key != "your_groq_api_key_here":
            self.llm = ChatGroq(
                temperature=0,
                groq_api_key=api_key,
                model_name=model_name
            )
        else:
            # Mock LLM for testing without API key
            self.llm = None

    def extract_jobs(self, cleaned_text):
        if self.llm is None:
            # Return mock data when no API key is available
            return [{
                "role": "Software Engineer",
                "experience": "2-3 years",
                "skills": ["Python", "JavaScript", "React", "Machine Learning"],
                "description": "We are looking for a talented Software Engineer to join our team. The ideal candidate will have experience with Python, JavaScript, and React."
            }]
            
        prompt_extract = PromptTemplate.from_template(
            """
            ### SCRAPED TEXT FROM WEBSITE:  
            {page_data}
            ### INSTRUCTION:
            Extract job postings from the above text and return them in valid JSON format.
            Each job should have these fields: {{"role"}}, {{"experience"}}, {{"skills"}}, {{"description"}}.
            Format the output as a JSON array, even for a single job.
            Ensure all text values are properly escaped and enclosed in double quotes.
            Keep descriptions concise to avoid context length issues.
            ### VALID JSON FORMAT EXAMPLE:
            [
                {{"role": "Software Engineer", "experience": "2-3 years", "skills": "Python, JavaScript", "description": "Brief description"}}
            ]
            ### OUTPUT JSON:
            """
        )
        chain_extract = prompt_extract | self.llm
        res = chain_extract.invoke(input={"page_data": cleaned_text})
        try:
            json_parser = JsonOutputParser()
            res = json_parser.parse(res.content)
            # Ensure result is always a list
            return res if isinstance(res, list) else [res]
        except OutputParserException:
            # If parsing fails, try to extract a smaller portion of the text
            if len(cleaned_text) > 2000:
                # Take first 2000 characters if text is too long
                return self.extract_jobs(cleaned_text[:2000])
            raise OutputParserException("Unable to parse jobs from the provided text.")

    def write_mail(self, job, links):
        if self.llm is None:
            # Return mock email when no API key is available
            return """Subject: Application for Software Engineer Position

Dear Hiring Manager,

We are writing to express our interest in the Software Engineer position at your company. As third-year Computer Science students at J.C. Bose University of Science and Technology with experience in Python, JavaScript, React, and Machine Learning, we believe we would be valuable additions to your team.

During our academic journey, we have worked on several projects that align with your requirements:
- Developed a machine learning model for predictive analytics using Python and TensorFlow
- Created a responsive web application using React and JavaScript
- Implemented efficient algorithms for data processing and analysis

We are particularly excited about the opportunity to contribute to innovative projects at your company and further develop our skills in a professional environment.

Please find our portfolio links below:
- GitHub (Shiv): https://github.com/shiv-portfolio
- Personal Website (Sakshi): https://sakshi-portfolio.dev

Thank you for considering our application. We look forward to the possibility of discussing how our skills and enthusiasm can contribute to your team.

Sincerely,
Shiv & Sakshi"""
            
        # Prepare skills for highlighting
        skills_val = job.get("skills", [])
        if isinstance(skills_val, list):
            skills_str = ", ".join([str(s) for s in skills_val])
        else:
            skills_str = str(skills_val)
        prompt_email = PromptTemplate.from_template(
            """
            ### JOB DESCRIPTION:
            {job_description}

            ### KEY SKILLS:
            {skills}

            ### INSTRUCTION:
            You are Shiv & Sakshi, Third-year Computer Science students at J.C. Bose University of Science and Technology.
            You are highly motivated and dedicated software engineering students with a strong passion for learning and continuous improvement.
            You are proactive team players eager to contribute to innovative projects and make a positive impact in software engineering,
            with skills in Machine Learning, Web Development, Mobile Development, and Data Structures & Algorithms.

            Write a concise, high-value cold email using at most 15–20 lines, clearly explaining how you (Shiv & Sakshi) can fulfill their needs.
            Also add the most relevant items from the following portfolio links: {link_list}
            Explicitly highlight all occurrences of the skill names from KEY SKILLS when they appear in the email body by wrapping each with HTML: <u><strong>Skill</strong></u>. Do NOT use color or <mark>.
            Keep the email professional and focused on outcomes, impact, reliability, and collaboration.
            Use a formal business email structure: a clear greeting (e.g., "Dear Hiring Manager"), a brief opening referencing the role/company, 1–2 short paragraphs with outcomes and relevant <u><strong>skills</strong></u>, a courteous closing ("Best regards,"), and a signature.
            Sign the email at the end with "Shiv & Sakshi".
            Do not provide a preamble.
            ### EMAIL (NO PREAMBLE):

            """
        )
        chain_email = prompt_email | self.llm
        res = chain_email.invoke({"job_description": str(job), "link_list": links, "skills": skills_str})
        return res.content

    def write_mail_variants(self, job, link_list, num_variants=None, tone="friendly", max_batch=10, platform="generic", link_content="", diversity="standard"):
        # Normalize links to a simple list of strings
        normalized_links = []
        if isinstance(link_list, list):
            # Flatten list-of-lists
            flat = []
            for item in link_list:
                if isinstance(item, list):
                    flat.extend(item)
                else:
                    flat.append(item)
            for item in flat:
                if isinstance(item, dict):
                    url = item.get("links") or item.get("url") or item.get("link")
                    if url:
                        normalized_links.append(url)
                else:
                    normalized_links.append(str(item))

        n = num_variants or (len(normalized_links) if normalized_links else 3)

        if self.llm is None:
            # Mock multiple variants when no API key is available
            variants = []
            for i in range(n):
                link = normalized_links[i % len(normalized_links)] if normalized_links else "https://github.com/shiv-portfolio"
                skills_val = job.get("skills", [])
                if isinstance(skills_val, list):
                    skills_markup = ", ".join([f"<u><strong>{str(s)}</strong></u>" for s in skills_val])
                else:
                    skills_markup = f"<u><strong>{str(skills_val)}</strong></u>" if skills_val else ""
                body_text = (
                    "Dear Hiring Manager,\n\n"
                    "We are writing to express our interest in the "
                    f"{job.get('role','position')} role. As third-year Computer Science students "
                    "at J.C. Bose University of Science and Technology, we bring hands-on experience "
                    "in Python, React, and end-to-end product delivery. Our work includes building data-driven "
                    "applications, optimizing performance, and collaborating cross-functionally to ship reliable features.\n\n"
                    "Portfolio highlight: " + link + "\n\n"
                )
                if skills_markup:
                    body_text += "Key Skills: " + skills_markup + "\n\n"
                body_text += (
                    "We would welcome the opportunity to discuss how we can help your team.\n\n"
                    "Best regards,\nShiv & Sakshi"
                )

                variants.append({
                    "subject": f"Application for {job.get('role','the role')} — Variant {i+1}",
                    "body": body_text
                })
            return variants

        prompt_variants = PromptTemplate.from_template(
            """
            ### JOB DESCRIPTION:
            {job_description}

            ### PORTFOLIO LINKS:
            {link_list}

            ### PORTFOLIO LINK CONTENT (for the primary link):
            {link_content}

            ### JOB PLATFORM:
            {platform}

            ### KEY SKILLS FROM JOB:
            {skills}

            ### INSTRUCTION:
            Create {n} distinct cold emails for this role. Each email must:
            - Use at most 15–20 lines (concise and high-value)
            - Be professional and conversational (AI-quality writing)
            - Follow formal business email structure: greeting, brief opening, 1–2 concise paragraphs focused on outcomes and relevant <u><strong>skills</strong></u>, courteous closing, and signature
            - Reference one portfolio link per email (rotate through the list if needed)
            - Vary the angle: technical depth, product impact, collaboration & reliability
            - Close with "Best regards," and sign off with "Shiv & Sakshi"
            - Use a {tone} tone. If "friendly", keep it warm, approachable, and professional; avoid slang.
            - Use the SAME portfolio link across all emails if a single link is provided (ignore extras).
            - Ensure each subject line is unique; vary patterns (benefit-led, value proposition, curiosity hook, project highlight, metrics).
            - Diversify style using this hint: {style_seed}. Lean into it to vary diction and structure, but DO NOT output this value.
            - Diversity mode: {diversity}. If "high", aggressively vary openings, structure (bulleted vs paragraph), rhetorical devices, and subject line patterns. Reduce phrase repetition.
            - If {platform} == "linkedin": write as a job application (concise value, role fit, relevant projects, call to interview).
            - If {platform} == "freelancing": write as a proposal (clear scope, deliverables, timeline, collaboration plan; optionally suggest a budget range if appropriate; include 1-2 clarifying questions).
            - Use PORTFOLIO LINK CONTENT to tailor claims and highlights; do not paste it verbatim, summarize and reference.
            - Explicitly highlight ALL skill names from KEY SKILLS when they appear by making them bold and underlined using HTML. Wrap skill tokens as <u><strong>Python</strong></u>, <u><strong>React</strong></u>, <u><strong>TensorFlow</strong></u>. Do NOT use color or <mark>. Keep the email flowing and professional; avoid over-marking non-skill words.

            Return ONLY valid JSON: a list where each item has keys "subject" and "body".
            Example format:
            [
              {{"subject": "Application for Software Engineer — Technical Focus", "body": "..."}},
              {{"subject": "Application for Software Engineer — Product Impact", "body": "..."}}
            ]
            """
        )
        chain_variants = prompt_variants | self.llm

        def _invoke_batch(batch_n):
            # Prepare skills string for highlighting
            skills_val = job.get("skills", [])
            if isinstance(skills_val, list):
                skills_str = ", ".join([str(s) for s in skills_val])
            else:
                skills_str = str(skills_val)
            res_local = chain_variants.invoke({
                "job_description": str(job),
                "link_list": normalized_links[:1] if normalized_links else ["https://github.com/shiv-portfolio"],
                "n": batch_n,
                "tone": tone,
                "style_seed": f"seed-{uuid.uuid4()}",
                "platform": platform,
                "link_content": link_content,
                "diversity": diversity,
                "skills": skills_str,
            })
            try:
                json_parser = JsonOutputParser()
                parsed = json_parser.parse(res_local.content)
                out_local = []
                for item in parsed if isinstance(parsed, list) else [parsed]:
                    subject = item.get("subject") if isinstance(item, dict) else None
                    body = item.get("body") if isinstance(item, dict) else None
                    if subject and body:
                        out_local.append({"subject": subject, "body": body})
                return out_local
            except OutputParserException:
                # Fallback to raw content split if possible
                return [{"subject": f"Application for {job.get('role','the role')}", "body": res_local.content}]

        # Batch across multiple invocations for large n
        aggregated = []
        remaining = n
        while remaining > 0:
            batch_n = min(max_batch, remaining)
            batch_out = _invoke_batch(batch_n)
            aggregated.extend(batch_out)
            remaining -= batch_n

        return aggregated


if __name__ == "__main__":
    print(os.getenv("GROQ_API_KEY"))
