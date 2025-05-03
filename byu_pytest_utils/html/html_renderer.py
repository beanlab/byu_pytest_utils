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
        Build HTML strings for observed and expected values with color-coded spans.
        """
        observed, expected = '', ''
        for o, e in zip(obs, exp):
            if o == gap:
                observed += f'<span style="background-color:rgba(212, 237, 218, 0.5); color:rgba(21, 87, 36, 0.8)">{o}</span>'
            elif e == gap:
                expected += f'<span style="background-color:rgba(248, 215, 218, 0.5); color:rgba(114, 28, 36, 0.8)">{e}</span>'
            elif o != e:
                observed += f'<span style="background-color:rgba(204, 229, 255, 0.5); color:rgba(0, 64, 133, 0.8)">{o}</span>'
                expected += f'<span style="background-color:rgba(204, 229, 255, 0.5); color:rgba(0, 64, 133, 0.8)">{e}</span>'
            else:
                observed += o
                expected += e

        # Handle remaining characters
        observed += ''.join(f'<span style="background-color:rgba(204, 229, 255, 0.5); color:rgba(0, 64, 133, 0.8)">{o}</span>' for o in obs[len(exp):])
        expected += ''.join(f'<span style="background-color:rgba(204, 229, 255, 0.5); color:rgba(0, 64, 133, 0.8)">{e}</span>' for e in exp[len(obs):])

        # Handle empty strings
        if not obs:
            observed = f'<span style="background-color:rgba(204, 229, 255, 0.5); color:rgba(0, 64, 133, 0.8)">{obs}</span>'
        if not exp:
            expected = f'<span style="background-color:rgba(204, 229, 255, 0.5); color:rgba(0, 64, 133, 0.8)">{exp}</span>'

        return observed, expected


if __name__ == '__main__':
    renderer = HTMLRenderer()
    score, obs, exp = edit_dist('hello', 'hallo')
    renderer.render('Test Case', score, obs, exp)