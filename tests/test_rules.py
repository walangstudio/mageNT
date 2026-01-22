"""Tests for the Rules system."""

import pytest
from rules import (
    RulesEngine,
    RulesConfig,
    RuleContext,
    RuleCategory,
    RuleSeverity,
    check_code,
)


class TestRulesEngine:
    """Test the main rules engine."""

    def test_engine_initialization(self):
        """Test that engine initializes with default config."""
        engine = RulesEngine()
        assert engine is not None
        rules = engine.list_rules()
        assert len(rules) > 0

    def test_check_clean_code(self):
        """Test checking code with no violations."""
        code = '''
def calculate_sum(numbers):
    """Calculate the sum of a list of numbers."""
    total = 0
    for num in numbers:
        total += num
    return total
'''
        # Exclude GIT category as it checks project config, not code quality
        report = check_code(code, "utils.py", categories=["security", "coding_style", "testing", "performance"])
        assert report.passed
        assert report.total_violations == 0

    def test_detect_hardcoded_secret(self):
        """Test detection of hardcoded secrets."""
        code = '''
API_KEY = "sk-ant-api03-1234567890abcdefghijklmnop"
'''
        engine = RulesEngine()
        report = engine.check_code(code, "config.py")

        assert not report.passed
        assert report.has_errors

        # Find the secret detection violation
        found_secret = False
        for result in report.results:
            for violation in result.violations:
                if "secret" in violation.rule_name.lower() or "api key" in violation.message.lower():
                    found_secret = True
                    break
        assert found_secret

    def test_detect_sql_injection(self):
        """Test detection of SQL injection vulnerabilities."""
        code = '''
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)
'''
        config = RulesConfig(enabled_categories={RuleCategory.SECURITY})
        engine = RulesEngine(config)
        report = engine.check_code(code, "database.py")

        # Should find SQL injection
        found_sql = False
        for result in report.results:
            if "sql" in result.rule_name.lower():
                found_sql = True
                break
        assert found_sql

    def test_detect_debug_statements(self):
        """Test detection of console.log/print statements."""
        code = '''
function processData(data) {
    console.log("Processing:", data);
    return data.map(x => x * 2);
}
'''
        config = RulesConfig(enabled_categories={RuleCategory.CODING_STYLE})
        engine = RulesEngine(config)
        report = engine.check_code(code, "processor.js")

        # Should find debug statement
        found_debug = False
        for result in report.results:
            for violation in result.violations:
                if "debug" in violation.rule_name.lower() or "console" in violation.message.lower():
                    found_debug = True
                    break
        assert found_debug

    def test_filter_by_category(self):
        """Test filtering rules by category."""
        config = RulesConfig(enabled_categories={RuleCategory.SECURITY})
        engine = RulesEngine(config)

        enabled_rules = engine.get_enabled_rules()
        for rule in enabled_rules:
            assert rule.category == RuleCategory.SECURITY

    def test_disable_specific_rule(self):
        """Test disabling a specific rule."""
        config = RulesConfig(disabled_rules={"no-hardcoded-secrets"})
        engine = RulesEngine(config)

        rules = engine.list_rules()
        assert not rules.get("no-hardcoded-secrets", {}).get("enabled", True)

    def test_get_guidance(self):
        """Test getting guidance for a rule."""
        engine = RulesEngine()
        guidance = engine.get_guidance("no-hardcoded-secrets")

        assert guidance is not None
        assert "environment" in guidance.lower() or "secret" in guidance.lower()

    def test_report_formatting(self):
        """Test that report formats correctly."""
        code = '''
password = "super_secret_password_123"
'''
        report = check_code(code, "config.py")
        text = report.format_text()

        assert "RULES VALIDATION REPORT" in text
        assert isinstance(text, str)

    def test_commit_message_validation(self):
        """Test commit message validation."""
        config = RulesConfig(enabled_categories={RuleCategory.GIT})
        engine = RulesEngine(config)

        # Good commit message
        context = RuleContext(
            metadata={"commit_message": "feat(auth): add login functionality"}
        )
        report = engine.check(context)
        # Should mostly pass (no errors)

        # Bad commit message
        context = RuleContext(
            metadata={"commit_message": "fixed stuff"}
        )
        report = engine.check(context)
        # Should have warnings about format


class TestSecurityRules:
    """Test security-specific rules."""

    def test_xss_detection(self):
        """Test XSS vulnerability detection."""
        code = '''
element.innerHTML = userInput;
'''
        config = RulesConfig(enabled_categories={RuleCategory.SECURITY})
        engine = RulesEngine(config)
        report = engine.check_code(code, "dom.js")

        # Should detect XSS
        found_xss = False
        for result in report.results:
            if "xss" in result.rule_name.lower():
                if not result.passed:
                    found_xss = True
        assert found_xss

    def test_eval_detection(self):
        """Test unsafe eval detection."""
        code = '''
eval(userInput)
'''
        config = RulesConfig(enabled_categories={RuleCategory.SECURITY})
        engine = RulesEngine(config)
        report = engine.check_code(code, "executor.py")

        # Should detect unsafe eval
        found_unsafe = False
        for result in report.results:
            for violation in result.violations:
                if "eval" in violation.message.lower() or "unsafe" in violation.message.lower():
                    found_unsafe = True
        assert found_unsafe


class TestPerformanceRules:
    """Test performance-specific rules."""

    def test_n1_query_detection(self):
        """Test N+1 query detection."""
        code = '''
for user in users:
    orders = db.query(Order).filter(user_id=user.id).all()
'''
        config = RulesConfig(enabled_categories={RuleCategory.PERFORMANCE})
        engine = RulesEngine(config)
        report = engine.check_code(code, "queries.py")

        # Should detect N+1 pattern
        found_n1 = False
        for result in report.results:
            if "n1" in result.rule_name.lower() or "n+1" in result.rule_name.lower():
                if not result.passed:
                    found_n1 = True
        assert found_n1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
