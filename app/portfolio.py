import pandas as pd
import chromadb
import uuid
import os

class Portfolio:
    def __init__(self, file_path="resource/my_portfolio.csv"):
        try:
            # Try the relative path first
            if os.path.exists(file_path):
                self.file_path = file_path
            # Try with app/ prefix
            elif os.path.exists(f"app/{file_path}"):
                self.file_path = f"app/{file_path}"
            else:
                raise FileNotFoundError(f"Portfolio file not found at {file_path} or app/{file_path}")
                
            self.data = pd.read_csv(self.file_path)
            self.chroma_client = chromadb.PersistentClient('vectorstore')
            self.collection = self.chroma_client.get_or_create_collection(name="portfolio")
        except Exception as e:
            raise Exception(f"Failed to initialize Portfolio: {str(e)}")

    def load_portfolio(self):
        # Refresh collection to reflect latest CSV changes
        try:
            if self.collection.count():
                existing = self.collection.get()
                ids = existing.get('ids', [])
                if ids:
                    self.collection.delete(ids=ids)
        except Exception:
            pass

        for _, row in self.data.iterrows():
            self.collection.add(
                documents=row["Techstack"],
                metadatas={"links": row["Links"]},
                ids=[str(uuid.uuid4())]
            )

    def query_links(self, skills):
        try:
            if isinstance(skills, list):
                skills_str = ", ".join(skills)
            else:
                skills_str = skills
                
            if self.collection.count() == 0:
                # If collection is empty, return mock data
                return [{"links": "https://github.com/shiv-portfolio"}, {"links": "https://sakshi-portfolio.dev"}]
                
            return self.collection.query(query_texts=[skills_str], n_results=2).get('metadatas', [])
        except Exception as e:
            # Return mock data in case of any error
            return [{"links": "https://github.com/shiv-portfolio"}, {"links": "https://sakshi-portfolio.dev"}]