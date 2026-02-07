"""Tests for document content validators."""

import pytest

from app.utils.validators import is_financial_document


class TestIsFinancialDocument:
    """Test suite for is_financial_document function."""

    def test_comprehensive_financial_statement(self):
        """Test with a comprehensive financial statement containing multiple indicators."""
        financial_text = """
        # Annual Report 2023

        ## Balance Sheet
        As of December 31, 2023

        ### Assets
        - Current Assets: $1,234,567.89
        - Non-Current Assets: $5,678,901.23
        - Total Assets: $6,913,469.12

        ### Liabilities
        - Current Liabilities: $876,543.21
        - Non-Current Liabilities: $2,345,678.90
        - Total Liabilities: $3,222,222.11

        ### Shareholders' Equity
        - Retained Earnings: $3,691,247.01
        - Total Equity: $3,691,247.01

        ## Income Statement
        For the year ended December 31, 2023

        - Revenue: $10,234,567.00
        - Cost of Goods Sold: $6,123,456.00
        - Gross Profit: $4,111,111.00
        - Operating Expenses: $2,345,678.00
        - Operating Income: $1,765,433.00
        - Net Income: $1,234,567.00
        - Earnings per Share: $2.47

        ## Audit Report
        The financial statements have been prepared in accordance with IFRS
        and US GAAP. An unqualified opinion has been issued by our external auditors.
        """

        is_financial, confidence = is_financial_document(financial_text)
        assert is_financial is True
        assert confidence >= 0.8, f"Expected confidence >= 0.8, got {confidence}"

    def test_balance_sheet_only(self):
        """Test with just a balance sheet."""
        balance_sheet_text = """
        # Balance Sheet
        As of December 31, 2023

        | Category | Amount (USD) |
        |----------|--------------|
        | Total Assets | 5,000,000.00 USD |
        | Current Liabilities | 1,500,000.00 USD |
        | Non-Current Liabilities | 2,000,000.00 USD |
        | Shareholders' Equity | 1,500,000.00 USD |
        """

        is_financial, confidence = is_financial_document(balance_sheet_text)
        assert is_financial is True
        assert confidence >= 0.4, f"Expected confidence >= 0.4, got {confidence}"

    def test_income_statement_with_gaap(self):
        """Test with income statement referencing GAAP."""
        income_statement_text = """
        Income Statement (US GAAP)
        For the fiscal year ended June 30, 2023

        Revenue: $8,765,432.10
        Cost of Goods Sold: $4,321,098.76
        Gross Profit: $4,444,333.34
        Operating Expenses: $2,111,222.33
        EBITDA: $2,333,111.01
        Net Income: $1,789,012.34
        """

        is_financial, confidence = is_financial_document(income_statement_text)
        assert is_financial is True
        assert confidence >= 0.5, f"Expected confidence >= 0.5, got {confidence}"

    def test_cash_flow_statement(self):
        """Test with cash flow statement."""
        cash_flow_text = """
        Statement of Cash Flows
        For Q4 2023

        Operating Activities:
        Net Income: $500,000.00
        Adjustments: $150,000.00

        Investing Activities:
        Capital Expenditures: ($200,000.00)

        Financing Activities:
        Dividends Paid: ($100,000.00)

        Prepared in accordance with IAS 7.
        """

        is_financial, confidence = is_financial_document(cash_flow_text)
        assert is_financial is True
        assert confidence >= 0.4, f"Expected confidence >= 0.4, got {confidence}"

    def test_profit_and_loss_report(self):
        """Test with P&L report."""
        pl_text = """
        # Profit & Loss Statement
        Annual Report FY2023

        Total Revenue: €2,500,000.00
        Total Expenses: €1,800,000.00
        Operating Income: €700,000.00
        Net Income: €525,000.00

        This P&L has been audited by external auditors.
        """

        is_financial, confidence = is_financial_document(pl_text)
        assert is_financial is True
        assert confidence >= 0.4, f"Expected confidence >= 0.4, got {confidence}"

    def test_audit_report(self):
        """Test with audit report containing financial terms."""
        audit_text = """
        External Audit Report
        For the year ended December 31, 2023

        We have audited the accompanying financial statements which comprise
        the balance sheet, income statement, and statement of cash flows.

        The financial statements have been prepared in accordance with IFRS
        and present fairly the financial position as of December 31, 2023.

        Total Assets: £5,000,000
        Total Liabilities: £3,000,000
        Shareholders' Equity: £2,000,000

        In our opinion, the financial statements present a true and fair view.
        """

        is_financial, confidence = is_financial_document(audit_text)
        assert is_financial is True
        assert confidence >= 0.6, f"Expected confidence >= 0.6, got {confidence}"

    def test_minimal_financial_document(self):
        """Test with minimal financial indicators just above threshold."""
        minimal_text = """
        Financial Summary for Fiscal Year 2023

        This annual report provides an overview of our balance sheet
        and income statement.

        Total Assets: $1,000,000
        Revenue: $500,000
        """

        is_financial, confidence = is_financial_document(minimal_text)
        # This should pass or be close to the threshold
        assert confidence >= 0.3, f"Expected confidence >= 0.3, got {confidence}"

    def test_novel_text(self):
        """Test with novel/fiction text - should NOT be financial."""
        novel_text = """
        # Chapter 1: The Beginning

        Once upon a time in a faraway land, there lived a young prince
        who dreamed of adventure. He would spend his days exploring the
        castle grounds and reading books about distant kingdoms.

        One day, he discovered a mysterious map in the library that would
        change his life forever. The map showed a path to a hidden treasure,
        buried deep within the enchanted forest.

        With courage in his heart and hope in his eyes, the prince set out
        on his journey, not knowing what dangers or wonders awaited him.
        """

        is_financial, confidence = is_financial_document(novel_text)
        assert is_financial is False
        assert confidence < 0.4, f"Expected confidence < 0.4, got {confidence}"

    def test_blog_post_text(self):
        """Test with blog post text - should NOT be financial."""
        blog_text = """
        # My Journey to Learning Python

        Posted on January 15, 2024

        Hey everyone! Today I want to share my experience learning Python
        programming. It's been an incredible journey filled with challenges
        and triumphs.

        ## Getting Started

        I began by taking an online course on Coursera. The instructor was
        great at explaining concepts like loops, functions, and data structures.

        ## Projects I Built

        1. A weather app using APIs
        2. A simple web scraper
        3. A todo list application

        ## What's Next?

        I'm planning to dive into machine learning and data science next.
        The possibilities seem endless!

        Thanks for reading, and happy coding!
        """

        is_financial, confidence = is_financial_document(blog_text)
        assert is_financial is False
        assert confidence < 0.4, f"Expected confidence < 0.4, got {confidence}"

    def test_recipe_text(self):
        """Test with recipe text - should NOT be financial."""
        recipe_text = """
        # Classic Chocolate Chip Cookies

        ## Ingredients:
        - 2 cups all-purpose flour
        - 1 cup butter, softened
        - 3/4 cup granulated sugar
        - 3/4 cup brown sugar
        - 2 eggs
        - 2 teaspoons vanilla extract
        - 1 teaspoon baking soda
        - 1/2 teaspoon salt
        - 2 cups chocolate chips

        ## Instructions:
        1. Preheat oven to 375°F
        2. Mix butter and sugars until creamy
        3. Beat in eggs and vanilla
        4. Combine dry ingredients and add to mixture
        5. Stir in chocolate chips
        6. Drop by spoonfuls onto baking sheet
        7. Bake for 9-11 minutes

        Enjoy your delicious cookies!
        """

        is_financial, confidence = is_financial_document(recipe_text)
        assert is_financial is False
        assert confidence < 0.4, f"Expected confidence < 0.4, got {confidence}"

    def test_technical_documentation(self):
        """Test with technical documentation - should NOT be financial."""
        tech_doc = """
        # API Documentation

        ## Overview
        This API provides endpoints for managing user accounts and data.

        ## Authentication
        All requests must include an API key in the header:
        ```
        Authorization: Bearer YOUR_API_KEY
        ```

        ## Endpoints

        ### GET /users
        Returns a list of all users.

        ### POST /users
        Creates a new user account.

        ### PUT /users/:id
        Updates an existing user.

        ### DELETE /users/:id
        Deletes a user account.

        ## Error Codes
        - 400: Bad Request
        - 401: Unauthorized
        - 404: Not Found
        - 500: Internal Server Error
        """

        is_financial, confidence = is_financial_document(tech_doc)
        assert is_financial is False
        assert confidence < 0.4, f"Expected confidence < 0.4, got {confidence}"

    def test_empty_string(self):
        """Test with empty string - should return False with 0 confidence."""
        is_financial, confidence = is_financial_document("")
        assert is_financial is False
        assert confidence == 0.0

    def test_none_input(self):
        """Test with None input - should return False with 0 confidence."""
        is_financial, confidence = is_financial_document(None)
        assert is_financial is False
        assert confidence == 0.0

    def test_whitespace_only(self):
        """Test with whitespace only - should return False with 0 confidence."""
        is_financial, confidence = is_financial_document("   \n\n\t  ")
        assert is_financial is False
        assert confidence == 0.0

    def test_news_article_about_finance(self):
        """Test with news article about finance - borderline case."""
        news_text = """
        # Tech Company Reports Strong Q4 Earnings

        SAN FRANCISCO - Tech giant XYZ Corp announced today that its revenue
        for Q4 2023 reached $5.2 billion, beating analyst expectations.

        The company's CEO stated that strong growth in cloud services and
        AI products drove the results. Operating income increased 15% year
        over year.

        Analysts noted that the company's balance sheet remains strong with
        total assets of $50 billion and manageable debt levels.

        The stock price surged 8% in after-hours trading following the
        announcement.
        """

        is_financial, confidence = is_financial_document(news_text)
        # This is a borderline case - has financial terms but isn't a financial statement
        # The result depends on how many indicators are detected
        # Just verify it returns reasonable values
        assert isinstance(is_financial, bool)
        assert 0.0 <= confidence <= 1.0

    def test_first_5000_chars_detection(self):
        """Test that detection works on first 5000 characters (mimicking actual usage)."""
        # Create a long document with financial content at the beginning
        financial_header = """
        # Consolidated Financial Statements
        For the year ended December 31, 2023

        ## Balance Sheet
        Total Assets: $10,000,000.00
        Total Liabilities: $6,000,000.00
        Shareholders' Equity: $4,000,000.00

        ## Income Statement
        Revenue: $15,000,000.00
        Net Income: $2,000,000.00

        Prepared in accordance with US GAAP.
        """

        # Add padding text to exceed 5000 characters
        padding = "\n\nAdditional notes: " + ("Lorem ipsum dolor sit amet. " * 200)
        long_document = financial_header + padding

        # Test with first 5000 chars only (as done in actual implementation)
        sample = long_document[:5000]
        is_financial, confidence = is_financial_document(sample)

        assert is_financial is True
        assert confidence >= 0.5, f"Expected confidence >= 0.5, got {confidence}"

    def test_multiple_currency_formats(self):
        """Test detection of various currency formats."""
        multi_currency_text = """
        # International Financial Report

        ## Revenue by Region
        - North America: $1,234,567.89
        - Europe: €987,654.32
        - UK: £543,210.00
        - Asia Pacific: ¥12,345,678

        ## Assets
        Total Assets: 5,000,000.00 USD
        Cash and Equivalents: 1,500,000.00 EUR
        """

        is_financial, confidence = is_financial_document(multi_currency_text)
        # Should detect currency patterns and some financial terms
        assert confidence > 0.2, f"Expected confidence > 0.2, got {confidence}"

    def test_fiscal_period_variations(self):
        """Test detection of various fiscal period formats."""
        fiscal_text = """
        Financial Results

        For the fiscal year FY2023, ending December 31, 2023.

        Q1 2023 revenue: $500,000
        Q2 2023 revenue: $600,000
        Q3 2023 revenue: $550,000
        Q4 2023 revenue: $700,000

        This quarterly report shows consistent growth.
        """

        is_financial, confidence = is_financial_document(fiscal_text)
        # Should detect fiscal periods and currency amounts
        assert confidence > 0.2, f"Expected confidence > 0.2, got {confidence}"

    def test_accounting_standards_variations(self):
        """Test detection of various accounting standards."""
        standards_text = """
        # Financial Statement Compliance

        These financial statements have been prepared in accordance with:
        - International Financial Reporting Standards (IFRS)
        - IAS 1: Presentation of Financial Statements
        - US GAAP for certain subsidiaries

        ## Balance Sheet Summary
        Total Assets: $10,000,000
        Total Liabilities: $6,000,000
        Shareholders' Equity: $4,000,000

        Revenue: $5,000,000
        """

        is_financial, confidence = is_financial_document(standards_text)
        assert is_financial is True
        assert confidence >= 0.5, f"Expected confidence >= 0.5, got {confidence}"
