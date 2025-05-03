import webbrowser
from pathlib import Path
from typing import Optional
from datetime import datetime
from byu_pytest_utils.edit_dist import edit_dist


def quote(url: str) -> str:
    return url.replace(' ', '%20').replace('\\', '/')


class HTMLRenderer:
    def __init__(self, template_path: Optional[Path] = None):
        self._html_template = template_path or (Path(__file__).parent / 'template.html')

    def render(
        self,
        test_name: str,
        score: float,
        obs: str,
        exp: str,
        gap: str = '~',
        result_path: Optional[Path] = None,
        open_in_browser: bool = True
    ) -> str:
        """
        Generate and optionally open an HTML file showing a comparison between observed and expected values.
        """
        # Read the HTML template
        if not self._html_template.exists():
            raise FileNotFoundError(f"Template not found at {self._html_template}")
        template = self._html_template.read_text(encoding="utf-8")

        # Build observed and expected strings
        observed, expected = self._build_comparison_strings(obs, exp, gap)

        # Generate timestamp
        timestamp = datetime.now().strftime("%B %d, %Y %I:%M %p")

        # Generate HTML content
        html_content = (
            template.replace('%%TEST_NAME%%', test_name)
            .replace('%%OBSERVED%%', observed)
            .replace('%%EXPECTED%%', expected)
            .replace('%%SCORE%%', str(score))
            .replace('%%TIMESTAMP%%', timestamp)
        )

        # Write final HTML to the result path
        result_path = result_path or (Path.cwd() / 'comparison_report.html')
        result_path.write_text(html_content, encoding='utf-8')

        # Open in browser if required
        url = f'file://{quote(str(result_path))}'
        print(f'Generated HTML report at {url}')
        if open_in_browser:
            webbrowser.open(url)
        return url

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
                color = "rgba(21, 87, 36, 0.8)"  # Green for gaps
                if current_obs_color != color:
                    if current_obs:
                        observed += wrap_span(current_obs, current_obs_color)
                    current_obs = o
                    current_obs_color = color
                else:
                    current_obs += o
            elif e == gap:
                color = "rgba(114, 28, 36, 0.8)"  # Red for gaps
                if current_exp_color != color:
                    if current_exp:
                        expected += wrap_span(current_exp, current_exp_color)
                    current_exp = e
                    current_exp_color = color
                else:
                    current_exp += e
            elif o != e:
                color = "rgba(100, 149, 237, 0.8)"  # Lighter blue for mismatches
                if current_obs_color != color:
                    if current_obs:
                        observed += wrap_span(current_obs, current_obs_color)
                    current_obs = o
                    current_obs_color = color
                else:
                    current_obs += o

                if current_exp_color != color:
                    if current_exp:
                        expected += wrap_span(current_exp, current_exp_color)
                    current_exp = e
                    current_exp_color = color
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
            observed += wrap_span(obs[len(exp):], "rgba(100, 149, 237, 0.8)")
        elif len(exp) > len(obs):
            expected += wrap_span(exp[len(obs):], "rgba(100, 149, 237, 0.8)")

        return observed, expected


if __name__ == '__main__':
    renderer = HTMLRenderer()
    score, obs, exp = edit_dist('hello', 'hallo')
    renderer.render('Test Case', score, obs, exp)