from pathlib import Path
from typing import Optional
from datetime import datetime
from bs4 import BeautifulSoup
from dataclasses import dataclass
import jinja2 as jj

# Highlight colors
RED = "rgba(255, 99, 71, 0.4)"        # mismatch
GREEN = "rgba(50, 205, 50, 0.4)"      # extra in observed
BLUE = "rgba(100, 149, 237, 0.4)"     # extra in expected


@dataclass
class ComparisonInfo:
    test_name: str
    score: float
    max_score: float
    observed: str
    expected: str
    passed: bool


class HTMLRenderer:
    def __init__(self, template_path: Optional[Path] = None):
        self.html_content: Optional[str] = None
        self._html_template = template_path or Path(__file__).parent / 'template.html.jinja'

    def render(
        self,
        comparison_info: list[ComparisonInfo],
        gap: str = '~',
    ) -> str:
        """Render HTML file with test comparison info and optionally open it."""
        if not self._html_template.exists():
            raise FileNotFoundError(f"Template not found at {self._html_template}")

        template = self._html_template.read_text(encoding="utf-8")

        jinja_args = {
            'COMPARISON_INFO': [
                (
                    info.test_name.replace('_', ' ').replace('-', ' ').title(),
                    *self._build_comparison_strings(info.observed, info.expected, gap),
                    info.score,
                    info.max_score,
                    'passed' if info.passed else 'failed',
                )
                for info in comparison_info
            ],
            'TESTS_PASSED': sum(info.passed for info in comparison_info),
            'TOTAL_TESTS': len(comparison_info),
            'TOTAL_SCORE': round(sum(info.score for info in comparison_info), 1),
            'TOTAL_POSSIBLE_SCORE': sum(info.max_score for info in comparison_info),
            'TIME': datetime.now().strftime("%B %d, %Y %I:%M %p")
        }

        html_content = jj.Template(template).render(**jinja_args)

        return html_content

    @staticmethod
    def get_comparison_results(html_content) -> list[str]:
        """Extract and return HTML strings of passed and failed test results."""

        soup = BeautifulSoup(html_content, 'html.parser')
        results = []

        for cls in ['test-result-passed', 'test-result-failed']:
            results.extend(str(div) for div in soup.find_all('div', class_=cls))

        return results

    @staticmethod
    def parse_info(results: dict) -> list[ComparisonInfo]:
        """Convert test result dictionary into a list of ComparisonInfo."""
        if len(results) != 1:
            raise ValueError("Expected exactly one key in results dictionary.")

        comparison_info = []
        for test_results in results.values():
            for result in test_results:
                comparison_info.append(ComparisonInfo(
                    test_name=result.get('name', ''),
                    score=result.get('score', 0),
                    max_score=result.get('max_score', 0),
                    observed=result.get('observed', ''),
                    expected=result.get('expected', ''),
                    passed=result.get('passed', False)
                ))

        return comparison_info

    @staticmethod
    def _build_comparison_strings(obs: str, exp: str, gap: str) -> tuple[str, str]:
        """Return observed and expected strings with HTML span highlighting."""
        def wrap_span(text: str, color: Optional[str]) -> str:
            return f'<span style="background-color:{color}; box-shadow: 0 0 0 {color};">{text}</span>' if text else ''

        observed, expected = '', ''
        curr_obs, curr_exp = '', ''
        obs_color, exp_color = None, None

        for o, e in zip(obs, exp):
            if o == gap:
                if obs_color != GREEN:
                    observed += wrap_span(curr_obs, obs_color)
                    curr_obs, obs_color = o, GREEN
                else:
                    curr_obs += o
            elif e == gap:
                if exp_color != RED:
                    expected += wrap_span(curr_exp, exp_color)
                    curr_exp, exp_color = e, RED
                else:
                    curr_exp += e
            elif o != e:
                if obs_color != BLUE:
                    observed += wrap_span(curr_obs, obs_color)
                    curr_obs, obs_color = o, BLUE
                else:
                    curr_obs += o

                if exp_color != BLUE:
                    expected += wrap_span(curr_exp, exp_color)
                    curr_exp, exp_color = e, BLUE
                else:
                    curr_exp += e
            else:
                observed += wrap_span(curr_obs, obs_color) + o
                expected += wrap_span(curr_exp, exp_color) + e
                curr_obs, curr_exp = '', ''
                obs_color = exp_color = None

        observed += wrap_span(curr_obs, obs_color)
        expected += wrap_span(curr_exp, exp_color)

        if len(obs) > len(exp):
            observed += wrap_span(obs[len(exp):], BLUE)
        elif len(exp) > len(obs):
            expected += wrap_span(exp[len(obs):], BLUE)

        return observed, expected
