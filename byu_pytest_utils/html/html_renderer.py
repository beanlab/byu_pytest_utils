import webbrowser
import jinja2 as jj

from pathlib import Path
from typing import Optional
from datetime import datetime
from bs4 import BeautifulSoup
from dataclasses import dataclass
from byu_pytest_utils.edit_dist import edit_dist

BLUE = "rgba(255, 99, 71, 0.4)"
GREEN = "rgba(50, 205, 50, 0.8)"
RED = "rgba(100, 149, 237, 0.4)"


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
        self._html_template = template_path or (Path(__file__).parent / 'template.html.jinja')

    def render(
        self,
        test_file_dir: Path,
        test_file_name: str,
        comparison_info: list[ComparisonInfo],
        gap: str = '~',
        headless: bool = True
    ) -> str | list[str]:
        """
        Generate and optionally open an HTML file showing a comparison between observed and expected values.
        """

        # Read the HTML template
        if not self._html_template.exists():
            raise FileNotFoundError(f"Template not found at {self._html_template}")
        template = self._html_template.read_text(encoding="utf-8")

        # Prepare test file name
        result_name = Path(test_file_name).stem
        file_name = result_name.replace('_', ' ').replace('-', ' ').title()

        # Generate jinja args
        jinja_args = {
            'TEST_FILE': file_name,
            'COMPARISON_INFO': [
                (
                    info.test_name.replace('_', ' ').replace('-', ' ').title(),
                    *self._build_comparison_strings(info.observed, info.expected, gap),
                    info.score,
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

        # Render the HTML content
        html_content = jj.Template(template).render(**jinja_args)

        # Write final HTML to the result path add the .html extension
        result_path = test_file_dir / f'{result_name}_results.html'
        result_path.write_text(html_content, encoding='utf-8')

        # Open in browser if required
        url = f'file://{self.quote(str(result_path))}'
        if headless:
            return self.get_comparisons(html_content)
        else:
            webbrowser.open(url)
            return url


    @staticmethod
    def parse_info(results: dict) -> list[ComparisonInfo]:
        """
        Parse the results dictionary and extract comparison information.
        """
        comparison_info = []

        assert len(results) == 1

        for _, test_results in results.items():

            for test_result in test_results:
                test_name = test_result.get('name', '')
                score = test_result.get('score', 0)
                max_score = test_result.get('max_score', 0)
                observed = test_result.get('observed', '')
                expected = test_result.get('expected', '')
                passed = test_result.get('passed', False)

                comparison_info.append(
                    ComparisonInfo(test_name, score, max_score, observed, expected, passed)
                )
        return comparison_info


    @staticmethod
    def get_comparisons(html_content: str) -> list[str]:
        """
        Extracts the observed and expected values from the HTML content.
        """
        comparisons = []

        soup = BeautifulSoup(html_content, 'html.parser')

        test_results = soup.find_all('div', class_='test-result-passed')
        for test_result in test_results:
            comparisons.append(str(test_result))

        test_results = soup.find_all('div', class_='test-result-failed')
        for test_result in test_results:
            comparisons.append(str(test_result))

        return comparisons


    @staticmethod
    def _build_comparison_strings(obs: str, exp: str, gap: str) -> tuple[str, str]:
        """
        Build HTML strings for observed and expected values with color-coded background styles.
        Wraps entire substrings in a single span tag instead of individual characters.
        """
        def wrap_span(content, color):
            return f'<span style="background-color:{color}; box-shadow: 0 0 0 {color};">{content}</span>'

        observed, expected = '', ''
        current_obs, current_exp = '', ''
        current_obs_color, current_exp_color = None, None

        for o, e in zip(obs, exp):
            if o == gap:
                if current_obs_color != GREEN:
                    if current_obs:
                        observed += wrap_span(current_obs, current_obs_color)
                    current_obs = o
                    current_obs_color = GREEN
                else:
                    current_obs += o
            elif e == gap:
                if current_exp_color != RED:
                    if current_exp:
                        expected += wrap_span(current_exp, current_exp_color)
                    current_exp = e
                    current_exp_color = RED
                else:
                    current_exp += e
            elif o != e:
                if current_obs_color != BLUE:
                    if current_obs:
                        observed += wrap_span(current_obs, current_obs_color)
                    current_obs = o
                    current_obs_color = BLUE
                else:
                    current_obs += o

                if current_exp_color != BLUE:
                    if current_exp:
                        expected += wrap_span(current_exp, current_exp_color)
                    current_exp = e
                    current_exp_color = BLUE
                else:
                    current_exp += e
            else:
                if current_obs:
                    observed += wrap_span(current_obs, current_obs_color)
                    current_obs = ''
                    current_obs_color = None
                if current_exp:
                    expected += wrap_span(current_exp, current_exp_color)
                    current_exp = ''
                    current_exp_color = None
                observed += o
                expected += e

        # Add remaining substrings
        if current_obs:
            observed += wrap_span(current_obs, current_obs_color)
        if current_exp:
            expected += wrap_span(current_exp, current_exp_color)

        # Handle remaining characters in longer strings
        if len(obs) > len(exp):
            observed += wrap_span(obs[len(exp):], BLUE)
        elif len(exp) > len(obs):
            expected += wrap_span(exp[len(obs):], BLUE)

        return observed, expected

    @staticmethod
    def quote(url: str) -> str:
        return url.replace(' ', '%20').replace('\\', '/')


if __name__ == '__main__':
    score1, obs1, exp1 = edit_dist('hello', 'hallo')
    score2, obs2, exp2 = edit_dist('bob', 'bob')

    test_comparison_info = [
        ComparisonInfo('Test 1', score1, obs1, exp1, False),
        ComparisonInfo('Test 3', score2, obs2, exp2, True)
    ]

    renderer = HTMLRenderer()
    renderer.render(
        test_file_dir=Path(__file__).parent,
        test_file_name='test',
        comparison_info=test_comparison_info
    )
