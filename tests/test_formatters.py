"""Unit tests for GitHub webhook event formatters."""

import unittest
import json
import os
import discord

# Add the parent directory to the path to import the formatters module
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from formatters import (
    format_workflow_run,
    format_workflow_job,
    format_check_run,
    format_check_suite,
    get_status_color,
    get_status_icon,
    calculate_duration,
)


class TestFormatters(unittest.TestCase):
    """Test cases for GitHub Actions formatters."""

    def setUp(self):
        """Set up test fixtures."""
        self.payload_dir = os.path.join(os.path.dirname(__file__), "payloads")

    def load_payload(self, filename):
        """Load a test payload from the payloads directory."""
        filepath = os.path.join(self.payload_dir, filename)
        with open(filepath, "r") as f:
            return json.load(f)

    def test_get_status_color(self):
        """Test status color mapping."""
        # Test conclusion-based colors
        self.assertEqual(
            get_status_color("completed", "success"), discord.Color.green()
        )
        self.assertEqual(get_status_color("completed", "failure"), discord.Color.red())
        self.assertEqual(
            get_status_color("completed", "cancelled"), discord.Color.light_grey()
        )

        # Test status-based colors
        self.assertEqual(get_status_color("queued"), discord.Color.orange())
        self.assertEqual(get_status_color("in_progress"), discord.Color.orange())
        self.assertEqual(get_status_color("cancelled"), discord.Color.light_grey())
        self.assertEqual(get_status_color("completed"), discord.Color.green())

    def test_get_status_icon(self):
        """Test status icon mapping."""
        # Test conclusion-based icons
        self.assertEqual(get_status_icon("completed", "success"), "✅")
        self.assertEqual(get_status_icon("completed", "failure"), "❌")
        self.assertEqual(get_status_icon("completed", "cancelled"), "🚫")

        # Test status-based icons
        self.assertEqual(get_status_icon("queued"), "⏳")
        self.assertEqual(get_status_icon("in_progress"), "🔄")
        self.assertEqual(get_status_icon("cancelled"), "🚫")
        self.assertEqual(get_status_icon("completed"), "✅")

    def test_calculate_duration(self):
        """Test duration calculation."""
        # Test valid timestamps
        start = "2023-01-01T12:00:00Z"
        end = "2023-01-01T12:03:45Z"
        self.assertEqual(calculate_duration(start, end), "3m 45s")

        # Test short duration
        start = "2023-01-01T12:00:00Z"
        end = "2023-01-01T12:00:30Z"
        self.assertEqual(calculate_duration(start, end), "30s")

        # Test missing timestamps
        self.assertEqual(calculate_duration(None, end), "N/A")
        self.assertEqual(calculate_duration(start, None), "N/A")
        self.assertEqual(calculate_duration(None, None), "N/A")

    def test_format_workflow_run_success(self):
        """Test workflow run formatter with successful run."""
        payload = self.load_payload("workflow_run.json")
        embed = format_workflow_run(payload)

        self.assertIsInstance(embed, discord.Embed)
        self.assertEqual(embed.title, "✅ Workflow Run: Build and Test")
        self.assertEqual(embed.color, discord.Color.green())
        self.assertTrue(embed.url.endswith("/actions/runs/1234567890"))

        # Check fields
        fields = {field.name: field.value for field in embed.fields}
        self.assertIn("Repository", fields)
        self.assertIn("Branch", fields)
        self.assertIn("Commit", fields)
        self.assertIn("Status", fields)
        self.assertIn("Duration", fields)
        self.assertIn("Run ID", fields)

        self.assertEqual(fields["Branch"], "main")
        self.assertEqual(fields["Status"], "Success")
        self.assertEqual(fields["Run ID"], "#1234567890")

    def test_format_workflow_run_failure(self):
        """Test workflow run formatter with failed run."""
        payload = self.load_payload("workflow_run_failed.json")
        embed = format_workflow_run(payload)

        self.assertIsInstance(embed, discord.Embed)
        self.assertEqual(embed.title, "❌ Workflow Run: Build and Test")
        self.assertEqual(embed.color, discord.Color.red())

        # Check fields
        fields = {field.name: field.value for field in embed.fields}
        self.assertEqual(fields["Branch"], "feature/bug-fix")
        self.assertEqual(fields["Status"], "Failure")

    def test_format_workflow_run_in_progress(self):
        """Test workflow run formatter with in-progress run."""
        payload = self.load_payload("workflow_run_in_progress.json")
        embed = format_workflow_run(payload)

        self.assertIsInstance(embed, discord.Embed)
        self.assertEqual(embed.title, "🔄 Workflow Run: Deploy to Production")
        self.assertEqual(embed.color, discord.Color.orange())

        # Check fields
        fields = {field.name: field.value for field in embed.fields}
        self.assertEqual(fields["Status"], "In Progress")

    def test_format_workflow_job(self):
        """Test workflow job formatter."""
        payload = self.load_payload("workflow_job.json")
        embed = format_workflow_job(payload)

        self.assertIsInstance(embed, discord.Embed)
        self.assertEqual(embed.title, "✅ Workflow Job: build")
        self.assertEqual(embed.color, discord.Color.green())
        self.assertTrue(embed.url.endswith("/jobs/9876543210"))

        # Check fields
        fields = {field.name: field.value for field in embed.fields}
        self.assertIn("Repository", fields)
        self.assertIn("Commit", fields)
        self.assertIn("Status", fields)
        self.assertIn("Duration", fields)
        self.assertIn("Job ID", fields)
        self.assertIn("Run ID", fields)

        self.assertEqual(fields["Status"], "Success")
        self.assertEqual(fields["Job ID"], "#9876543210")
        self.assertEqual(fields["Run ID"], "#1234567890")

    def test_format_check_run(self):
        """Test check run formatter."""
        payload = self.load_payload("check_run.json")
        embed = format_check_run(payload)

        self.assertIsInstance(embed, discord.Embed)
        self.assertEqual(embed.title, "✅ Check Run: CI")
        self.assertEqual(embed.color, discord.Color.green())
        self.assertTrue(embed.url.endswith("/actions/runs/1234567890"))

        # Check fields
        fields = {field.name: field.value for field in embed.fields}
        self.assertIn("Repository", fields)
        self.assertIn("Branch", fields)
        self.assertIn("Commit", fields)
        self.assertIn("Status", fields)
        self.assertIn("Duration", fields)
        self.assertIn("Check ID", fields)

        self.assertEqual(fields["Branch"], "main")
        self.assertEqual(fields["Status"], "Success")
        self.assertEqual(fields["Check ID"], "#4567890123")

    def test_format_check_suite(self):
        """Test check suite formatter."""
        payload = self.load_payload("check_suite.json")
        embed = format_check_suite(payload)

        self.assertIsInstance(embed, discord.Embed)
        self.assertEqual(embed.title, "✅ Check Suite: GitHub Actions")
        self.assertEqual(embed.color, discord.Color.green())
        self.assertTrue("/commits/" in embed.url and "/checks" in embed.url)

        # Check fields
        fields = {field.name: field.value for field in embed.fields}
        self.assertIn("Repository", fields)
        self.assertIn("Branch", fields)
        self.assertIn("Commit", fields)
        self.assertIn("Status", fields)
        self.assertIn("Duration", fields)
        self.assertIn("Suite ID", fields)

        self.assertEqual(fields["Branch"], "main")
        self.assertEqual(fields["Status"], "Success")
        self.assertEqual(fields["Suite ID"], "#5678901234")

    def test_format_workflow_run_missing_data(self):
        """Test workflow run formatter with missing data."""
        payload = {"workflow_run": {}, "repository": {}}
        embed = format_workflow_run(payload)

        self.assertIsInstance(embed, discord.Embed)
        self.assertEqual(embed.title, "❓ Workflow Run: Unknown Workflow")

        # Check that it handles missing data gracefully
        fields = {field.name: field.value for field in embed.fields}
        self.assertEqual(fields["Branch"], "unknown")
        self.assertEqual(fields["Status"], "Unknown")
        self.assertEqual(fields["Duration"], "N/A")


if __name__ == "__main__":
    unittest.main()
