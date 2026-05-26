#!/usr/bin/env python3
"""
RNA Development Tracker - Daily Search Script
Searches PubMed, arXiv, and Semantic Scholar for RNA research updates
"""

import requests
import json
import csv
from datetime import datetime, timedelta
import time
import os
from urllib.parse import quote

# API endpoints
PUBMED_API_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ARXIV_API = "http://export.arxiv.org/api/query?"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"

# RNA research categories
RNA_CATEGORIES = {
    "mRNA Therapeutics": [
        "mRNA", "messenger RNA", "mRNA vaccine", "mRNA therapy",
        "mRNA therapeutic", "mRNA drug", "mRNA medicine"
    ],
    "RNAi & Gene Silencing": [
        "RNAi", "siRNA", "shRNA", "gene silencing",
        "RNA interference", "small interfering"
    ],
    "Long Non-Coding RNA": [
        "lncRNA", "long non-coding RNA", "long noncoding",
        "lnc-RNA", "lncRNA function"
    ],
    "RNA Delivery": [
        "RNA delivery", "nanoparticle", "LNP",
        "lipid nanoparticle", "mRNA delivery", "ionizable lipid",
        "delivery system"
    ],
    "RNA Vaccines": [
        "RNA vaccine", "mRNA vaccine", "vaccine development",
        "immunotherapy", "cancer vaccine"
    ],
    "Clinical & Regulatory": [
        "clinical trial", "FDA approval", "approved",
        "CLIA", "regulatory approval", "patient treatment"
    ],
}

class RNATracker:
    def __init__(self):
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        self.results = []
        
    def search_pubmed(self, query):
        """Search PubMed for publications"""
        try:
            print(f"  Searching PubMed for: {query}")
            
            # Search query
            search_url = f"{PUBMED_API_BASE}/esearch.fcgi"
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": 50,
                "rettype": "json",
                "sort": "date"
            }
            
            resp = requests.get(search_url, params=search_params, timeout=10)
            resp.raise_for_status()
            ids = resp.json().get("esearchresult", {}).get("idlist", [])
            
            if not ids:
                return []
            
            # Fetch details
            fetch_url = f"{PUBMED_API_BASE}/efetch.fcgi"
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(ids[:20]),
                "rettype": "json"
            }
            
            fetch_resp = requests.get(fetch_url, params=fetch_params, timeout=10)
            fetch_resp.raise_for_status()
            articles = fetch_resp.json().get("result", {})
            
            results = []
            for uid in ids[:20]:
                if uid in articles and uid != "uids":
                    art = articles[uid]
                    
                    # Extract information
                    title = art.get("title", "")
                    abstract = art.get("abstract", "")[:300]
                    
                    authors = []
                    for author in art.get("authors", [])[:3]:
                        authors.append(author.get("name", ""))
                    
                    result = {
                        "title": title,
                        "abstract": abstract,
                        "authors": ", ".join(authors),
                        "journal": art.get("journal", ""),
                        "date": self.today,
                        "link": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                        "source": "PubMed"
                    }
                    results.append(result)
            
            return results
        except Exception as e:
            print(f"  PubMed error: {e}")
            return []
    
    def search_arxiv(self, query):
        """Search arXiv for preprints"""
        try:
            print(f"  Searching arXiv for: {query}")
            
            arxiv_query = f"cat:q-bio.BM AND all:{query}"
            
            params = {
                "search_query": arxiv_query,
                "start": 0,
                "max_results": 30,
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            }
            
            resp = requests.get(ARXIV_API, params=params, timeout=10)
            resp.raise_for_status()
            
            # Parse XML response
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(resp.content)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
            except:
                return []
            
            results = []
            for entry in root.findall("atom:entry", ns)[:20]:
                try:
                    title_elem = entry.find("atom:title", ns)
                    summary_elem = entry.find("atom:summary", ns)
                    link_elem = entry.find("atom:id", ns)
                    
                    if all([title_elem is not None, summary_elem is not None, link_elem is not None]):
                        title = title_elem.text.strip()
                        summary = summary_elem.text.strip()[:300]
                        link = link_elem.text.strip()
                        
                        result = {
                            "title": title,
                            "abstract": summary,
                            "authors": "arXiv contributors",
                            "journal": "arXiv",
                            "date": self.today,
                            "link": link,
                            "source": "arXiv"
                        }
                        results.append(result)
                except:
                    continue
            
            return results
        except Exception as e:
            print(f"  arXiv error: {e}")
            return []
    
    def search_semantic_scholar(self, query):
        """Search Semantic Scholar"""
        try:
            print(f"  Searching Semantic Scholar for: {query}")
            
            params = {
                "query": query,
                "limit": 50,
                "fields": "title,abstract,url,venue,publicationDate,authors"
            }
            
            resp = requests.get(SEMANTIC_SCHOLAR_API, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            results = []
            for paper in data.get("data", [])[:20]:
                title = paper.get("title", "")
                abstract = paper.get("abstract", "")
                
                if abstract:
                    abstract = abstract[:300]
                
                authors = []
                for author in paper.get("authors", [])[:3]:
                    authors.append(author.get("name", ""))
                
                result = {
                    "title": title,
                    "abstract": abstract or "",
                    "authors": ", ".join(authors),
                    "journal": paper.get("venue", ""),
                    "date": self.today,
                    "link": paper.get("url", ""),
                    "source": "Semantic Scholar"
                }
                results.append(result)
            
            return results
        except Exception as e:
            print(f"  Semantic Scholar error: {e}")
            return []
    
    def categorize_results(self, all_results):
        """Categorize results by RNA type"""
        categories = {cat: [] for cat in RNA_CATEGORIES}
        categories["General RNA Research"] = []
        
        for paper in all_results:
            title_lower = paper["title"].lower()
            abstract_lower = paper["abstract"].lower()
            text = f"{title_lower} {abstract_lower}"
            
            categorized = False
            
            for category, keywords in RNA_CATEGORIES.items():
                if any(keyword.lower() in text for keyword in keywords):
                    categories[category].append(paper)
                    categorized = True
                    break
            
            if not categorized:
                categories["General RNA Research"].append(paper)
        
        return categories
    
    def generate_report(self, categories):
        """Generate markdown report"""
        report = f"# RNA Development Updates - {self.today}\n\n"
        report += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        
        total = sum(len(v) for v in categories.values())
        report += f"## Summary\n- Total publications found: {total}\n"
        report += f"- Sources: PubMed, arXiv, Semantic Scholar\n\n---\n\n"
        
        for category, papers in categories.items():
            if papers:
                report += f"## {category} ({len(papers)} publications)\n\n"
                
                for i, paper in enumerate(papers, 1):
                    report += f"### {i}. {paper['title']}\n"
                    report += f"**Journal/Venue:** {paper['journal']} | **Source:** {paper['source']}\n\n"
                    report += f"**Authors:** {paper['authors']}\n\n"
                    
                    if paper['abstract']:
                        report += f"**Abstract:** {paper['abstract']}...\n\n"
                    
                    report += f"**Link:** [{paper['link']}]({paper['link']})\n\n"
                    report += "---\n\n"
        
        return report
    
    def run(self):
        """Execute full search workflow"""
        print(f"\nStarting RNA research search for {self.today}...")
        print(f"This may take 3-5 minutes...\n")
        
        # Search queries
        search_queries = [
            "mRNA",
            "RNA interference",
            "lncRNA",
            "RNA delivery",
            "RNA vaccine",
            "siRNA"
        ]
        
        # Search all sources
        for query in search_queries:
            print(f"Processing: {query}")
            self.results.extend(self.search_pubmed(query))
            self.results.extend(self.search_arxiv(query))
            self.results.extend(self.search_semantic_scholar(query))
            time.sleep(1)  # Rate limiting
        
        # Remove duplicates by title
        unique_results = []
        seen_titles = set()
        for paper in self.results:
            if paper["title"] not in seen_titles:
                unique_results.append(paper)
                seen_titles.add(paper["title"])
        
        print(f"\nFound {len(unique_results)} unique publications\n")
        
        # Categorize
        categories = self.categorize_results(unique_results)
        
        # Generate report
        report = self.generate_report(categories)
        
        # Create reports directory
        os.makedirs("reports", exist_ok=True)
        
        # Save markdown report
        report_file = f"reports/rna_update_{self.today}.md"
        with open(report_file, "w") as f:
            f.write(report)
        print(f"✓ Report saved: {report_file}")
        
        # Save JSON data
        json_file = f"reports/rna_data_{self.today}.json"
        with open(json_file, "w") as f:
            json.dump({
                "date": self.today,
                "total_results": len(unique_results),
                "results": unique_results,
                "categories": {k: len(v) for k, v in categories.items()}
            }, f, indent=2, default=str)
        print(f"✓ Data saved: {json_file}")
        
        # Save CSV
        if unique_results:
            csv_file = f"reports/rna_data_{self.today}.csv"
            with open(csv_file, "w", newline="") as f:
                writer = csv.DictWriter(
                    f, 
                    fieldnames=["title", "authors", "journal", "date", "abstract", "link", "source"]
                )
                writer.writeheader()
                writer.writerows(unique_results)
            print(f"✓ CSV saved: {csv_file}")
        
        print(f"\nDone! All reports saved to /reports/ folder.\n")

if __name__ == "__main__":
    tracker = RNATracker()
    tracker.run()
