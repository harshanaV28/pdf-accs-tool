"""
Generate Demonstration Reports
Runs the PDF Accessibility Inspector engine on sample documents
and outputs PDF, HTML, JSON, and CSV reports into the sample_reports/ directory.
"""

import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.engine.runner import AuditRunner
from src.pdf_inspector.reporting.pdf_report import PDFReportGenerator
from src.pdf_inspector.reporting.html_report import HTMLReportGenerator
from src.pdf_inspector.reporting.json_exporter import JSONExporter, CSVExporter
from scripts.generate_sample_pdfs import generate_samples


def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    samples_dir = os.path.join(root_dir, "test_samples")
    reports_dir = os.path.join(root_dir, "sample_reports")
    os.makedirs(reports_dir, exist_ok=True)

    acc_pdf, inacc_pdf = generate_samples(samples_dir)
    runner = AuditRunner()

    for pdf_path in [acc_pdf, inacc_pdf]:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        print(f"Auditing {base_name}...")
        parser = DocumentParser(pdf_path)
        doc = parser.parse()
        report = runner.run(doc)

        # 1. PDF Report
        pdf_out = os.path.join(reports_dir, f"{base_name}_audit_report.pdf")
        PDFReportGenerator.generate(report, pdf_out)

        # 2. HTML Report
        html_out = os.path.join(reports_dir, f"{base_name}_audit_report.html")
        HTMLReportGenerator.generate(report, html_out)

        # 3. JSON Export
        json_out = os.path.join(reports_dir, f"{base_name}_audit_report.json")
        JSONExporter.export(report, json_out)

        # 4. CSV Export
        csv_out = os.path.join(reports_dir, f"{base_name}_findings.csv")
        CSVExporter.export(report, csv_out)

        print(f"  -> Generated: {pdf_out}")
        print(f"  -> Generated: {html_out}")
        print(f"  -> Generated: {json_out}")
        print(f"  -> Generated: {csv_out}")

    print(f"\nAll sample reports generated in {reports_dir}")


if __name__ == "__main__":
    main()
