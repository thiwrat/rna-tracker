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
import xml.etree.ElementTree as ET

# API endpoints
PUBMED_API_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ARXIV_API = "http://export.arxiv.org/api/query"
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
        """Search PubMed using esearch + efetch with XML (most reliable)"""
        try:
            print(f"  [PubMed] Searching: {query}")

            # Step 1: esearch to get IDs
            search_url = f"{PUBMED_API_BASE}/esearch.fcgi"
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": 20,
                "retmode": "json",
                "sort": "date"
            }
            resp = requests.get(search_url, params=search_params, timeout=15)
            resp.raise_for_status()
            ids = resp.json().get("esearchresult", {}).get("idlist", [])

            if not ids:
                print(f"  [PubMed] No results for: {query}")
                return []

            print(f"  [PubMed] Found {len(ids)} IDs, fetching details...")

            # Step 2: efetch with XML to get full records including abstracts
            fetch_url = f"{PUBMED_API_BASE}/efetch.fcgi"
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(ids[:20]),
                "rettype": "abstract",
                "retmode": "xml"
            }
            fetch_resp = requests.get(fetch_url, params=fetch_params, timeout=15)
            fetch_resp.raise_for_status()

            # Parse XML
            root = ET.fromstring(fetch_resp.content)
            results = []

            for article in root.findall(".//PubmedArticle"):
                try:
                    # Title
                    title_elem = article.find(".//ArticleTitle")
                    title = title_elem.text if title_elem is not None else ""
                    if not title:
                        continue

                    # Abstract
                    abstract_parts = article.findall(".//AbstractText")
                    abstract = " ".join(
                        (a.text or "") for a in abstract_parts if a.text
                    )[:400]

                    # Authors
                    authors = []
                    for author in article.findall(".//Author")[:3]:
                        last = author.find("LastName")
                        fore = author.find("ForeName")
                        if last is not None:
                            name = last.text
                            if fore is not None:
                                name += f" {fore.text}"
                            authors.append(name)

                    # Journal
                    journal_elem = article.find(".//Journal/Title")
                    journal = journal_elem.text if journal_elem is not None else ""

                    # PMID
                    pmid_elem = article.find(".//PMID")
                    pmid = pmid_elem.text if pmid_elem is not None else ""

                    results.append({
                        "title": title,
                        "abstract": abstract,
                        "authors": ", ".join(authors),
                        "journal": journal,
                        "date": self.today,
                        "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        "source": "PubMed"
                    })
                except Exception as e:
                    print(f"  [PubMed] Error parsing article: {e}")
                    continue

            print(f"  [PubMed] Parsed {len(results)} articles")
            return results

        except Exception as e:
            print(f"  [PubMed] ERROR: {e}")
            return []

    def search_arxiv(self, query):
        """Search arXiv for preprints"""
        try:
            print(f"  [arXiv] Searching: {query}")

            params = {
                "search_query": f"cat:q-bio.BM AND all:{query}",
                "start": 0,
                "max_results": 20,
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            }

            resp = requests.get(ARXIV_API, params=params, timeout=15)
            resp.raise_for_status()

            root = ET.fromstring(resp.content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            results = []
            for entry in root.findall("atom:entry", ns)[:20]:
                try:
                    title_elem = entry.find("atom:title", ns)
                    summary_elem = entry.find("atom:summary", ns)
                    link_elem = entry.find("atom:id", ns)

                    if title_elem is None or link_elem is None:
                        continue

                    title = title_elem.text.strip().replace("\n", " ")
                    summary = summary_elem.text.strip()[:400] if summary_elem is not None else ""
                    link = link_elem.text.strip()

                    # Authors
                    authors = []
                    for author in entry.findall("atom:author", ns)[:3]:
                        name_elem = author.find("atom:name", ns)
                        if name_elem is not None:
                            authors.append(name_elem.text)

                    results.append({
                        "title": title,
                        "abstract": summary,
                        "authors": ", ".join(authors),
                        "journal": "arXiv",
                        "date": self.today,
                        "link": link,
                        "source": "arXiv"
                    })
                except Exception as e:
                    print(f"  [arXiv] Error parsing entry: {e}")
                    continue

            print(f"  [arXiv] Parsed {len(results)} articles")
            return results

        except Exception as e:
            print(f"  [arXiv] ERROR: {e}")
            return []

    def search_semantic_scholar(self, query):
        """Search Semantic Scholar with correct headers and error handling"""
        try:
            print(f"  [SemanticScholar] Searching: {query}")

            headers = {
                "User-Agent": "RNA-Tracker/1.0 (research tool)"
            }
            params = {
                "query": query,
                "limit": 20,
                "fields": "title,abstract,url,venue,publicationDate,authors"
            }

            resp = requests.get(
                SEMANTIC_SCHOLAR_API,
                params=params,
                headers=headers,
                timeout=15
            )

            if resp.status_code == 429:
                print(f"  [SemanticScholar] Rate limited, skipping...")
                return []

            resp.raise_for_status()
            data = resp.json()

            results = []
            for paper in data.get("data", [])[:20]:
                title = paper.get("title", "")
                if not title:
                    continue

                abstract = paper.get("abstract") or ""
                abstract = abstract[:400]

                authors = []
                for author in paper.get("authors", [])[:3]:
                    authors.append(author.get("name", ""))

                results.append({
                    "title": title,
                    "abstract": abstract,
                    "authors": ", ".join(authors),
                    "journal": paper.get("venue", ""),
                    "date": paper.get("publicationDate") or self.today,
                    "link": paper.get("url", ""),
                    "source": "Semantic Scholar"
                })

            print(f"  [SemanticScholar] Parsed {len(results)} articles")
            return results

        except Exception as e:
            print(f"  [SemanticScholar] ERROR: {e}")
            return []

    def categorize_results(self, all_results):
        """Categorize results by RNA type"""
        categories = {cat: [] for cat in RNA_CATEGORIES}
        categories["General RNA Research"] = []

        for paper in all_results:
            text = f"{paper['title'].lower()} {paper['abstract'].lower()}"
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

        # Per-source counts
        source_counts = {}
        for papers in categories.values():
            for p in papers:
                source_counts[p["source"]] = source_counts.get(p["source"], 0) + 1
        for src, count in source_counts.items():
            report += f"- {src}: {count} publications\n"
        report += "\n---\n\n"

        for category, papers in categories.items():
            if papers:
                report += f"## {category} ({len(papers)} publications)\n\n"
                for i, paper in enumerate(papers, 1):
                    report += f"### {i}. {paper['title']}\n"
                    report += f"**Source:** {paper['source']} | **Journal/Venue:** {paper['journal']}\n\n"
                    report += f"**Authors:** {paper['authors']}\n\n"
                    if paper["abstract"]:
                        report += f"**Abstract:** {paper['abstract']}...\n\n"
                    report += f"**Link:** [{paper['link']}]({paper['link']})\n\n"
                    report += "---\n\n"

        return report

    def run(self):
        """Execute full search workflow"""
        print(f"\nStarting RNA research search for {self.today}...")
        print(f"This may take 3-5 minutes...\n")

        search_queries = [
            "mRNA",
            "RNA interference",
            "lncRNA",
            "RNA delivery",
            "RNA vaccine",
            "siRNA"
        ]

        for query in search_queries:
            print(f"\nProcessing query: '{query}'")
            self.results.extend(self.search_pubmed(query))
            time.sleep(1)
            self.results.extend(self.search_arxiv(query))
            time.sleep(1)
            self.results.extend(self.search_semantic_scholar(query))
            time.sleep(2)  # Slightly longer pause for Semantic Scholar

        # Deduplicate by title
        unique_results = []
        seen_titles = set()
        for paper in self.results:
            title_key = paper["title"].lower().strip()
            if title_key and title_key not in seen_titles:
                unique_results.append(paper)
                seen_titles.add(title_key)

        print(f"\n{'='*50}")
        print(f"Found {len(unique_results)} unique publications")
        print(f"{'='*50}\n")

        # Categorize & report
        categories = self.categorize_results(unique_results)
        report = self.generate_report(categories)

        os.makedirs("reports", exist_ok=True)

        report_file = f"reports/rna_update_{self.today}.md"
        with open(report_file, "w") as f:
            f.write(report)
        print(f"Report saved: {report_file}")

        json_file = f"reports/rna_data_{self.today}.json"
        with open(json_file, "w") as f:
            json.dump({
                "date": self.today,
                "total_results": len(unique_results),
                "results": unique_results,
                "categories": {k: len(v) for k, v in categories.items()}
            }, f, indent=2, default=str)
        print(f"Data saved: {json_file}")

        if unique_results:
            csv_file = f"reports/rna_data_{self.today}.csv"
            with open(csv_file, "w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["title", "authors", "journal", "date", "abstract", "link", "source"]
                )
                writer.writeheader()
                writer.writerows(unique_results)
            print(f"CSV saved: {csv_file}")

        print(f"\nDone! All reports saved to /reports/ folder.\n")


if __name__ == "__main__":
    tracker = RNATracker()
    tracker.run()
