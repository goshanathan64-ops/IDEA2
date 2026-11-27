import unittest
from blueprint_intelligence import (analyze_blueprint_intelligence, render_blueprint_intelligence_summary,
    recommend_blueprint_improvements, render_blueprint_improvements)

class BlueprintIntelligenceTests(unittest.TestCase):
    def test_complete_blueprint_is_high_confidence(self):
        report = analyze_blueprint_intelligence({"name":"Village Shop","description":"Track products and sales","target":"Tuckshop owners","template_id":"shop_inventory","app_type":"Business","features":"products, stock, sales"},{"unsupported":[],"ready":True})
        self.assertEqual(report["completeness"],100)
        self.assertEqual(report["confidence"],"HIGH")
        self.assertEqual(report["missing_fields"],[])

    def test_sparse_blueprint_recommends_missing_details(self):
        report = analyze_blueprint_intelligence({"name":"Quick App"})
        self.assertEqual(report["completeness"],20)
        self.assertEqual(report["confidence"],"LOW")
        self.assertIn("description",report["missing_fields"])
        self.assertIn("target",report["missing_fields"])
        self.assertTrue(report["recommendations"])

    def test_ambiguous_featureless_blueprint_is_advisory(self):
        report = analyze_blueprint_intelligence({"name":"My App","description":"A simple app","target":"Everyone","template_id":"shop_inventory","features":""})
        self.assertTrue(report["ready_for_review"])
        self.assertTrue(any(i["type"]=="no_features_listed" for i in report["issues"]))

    def test_unsupported_features_are_reported_not_removed(self):
        report = analyze_blueprint_intelligence({"name":"Customers","description":"Manage customers","target":"Shop owners","template_id":"customer_manager","features":"bulk_sms"},{"unsupported":["bulk_sms"],"ready":True})
        issue = next(i for i in report["issues"] if i["type"]=="unsupported_features")
        self.assertEqual(issue["items"],["bulk_sms"])
        self.assertTrue(any("unsupported" in r.lower() for r in report["recommendations"]))

    def test_app_type_template_mismatch_warning(self):
        report = analyze_blueprint_intelligence({"name":"School App","description":"Manage attendance","target":"Teachers","template_id":"shop_inventory","app_type":"School"})
        self.assertTrue(any(i["type"]=="app_type_template_mismatch" for i in report["issues"]))

    def test_unknown_template_is_reported_without_blocking_review(self):
        report = analyze_blueprint_intelligence({"name":"New App","description":"A new app","target":"Users","template_id":"future_template"},{"unsupported":[],"ready":False})
        self.assertTrue(any(i["type"]=="unknown_template" for i in report["issues"]))
        self.assertTrue(report["ready_for_review"])

    def test_improvements_are_supported_and_do_not_mutate_blueprint(self):
        data = {"template_id":"shop_inventory","features":"record_sales"}
        before = dict(data)
        suggestions = recommend_blueprint_improvements(data, {"requested":["record_sales"]})
        self.assertTrue(suggestions)
        self.assertTrue(all(item["feature"] in {"product_catalogue","stock_tracking","basic_reports","local_sqlite_storage"} for item in suggestions))
        self.assertEqual(data, before)

    def test_improvements_skip_existing_features_and_unknown_templates(self):
        data = {"template_id":"task_manager","features":"tasks, due dates"}
        suggestions = recommend_blueprint_improvements(data)
        names = [item["feature"] for item in suggestions]
        self.assertNotIn("task_records", names)
        self.assertNotIn("due_dates", names)
        self.assertEqual(recommend_blueprint_improvements({"template_id":"future_template"}), [])

    def test_improvement_renderer_is_clear_when_empty(self):
        self.assertIn("No additional", render_blueprint_improvements([]))
        self.assertIn("OPTIONAL IMPROVEMENTS", render_blueprint_improvements([{"feature":"basic_reports","reason":"Summarize records."}]))

    def test_summary_format_includes_score_and_recommendation(self):
        report = analyze_blueprint_intelligence({"name":"My App"})
        rendered = render_blueprint_intelligence_summary(report)
        self.assertIn("20% COMPLETE", rendered)
        self.assertIn("LOW CONFIDENCE", rendered)
        self.assertIn("SUGGESTION:", rendered)

if __name__ == "__main__": unittest.main()
