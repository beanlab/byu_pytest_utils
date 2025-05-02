import os
import webbrowser
from pathlib import Path

from byu_pytest_utils.edit_dist import edit_dist


def quote(url):
    return (
        url
        .replace(' ', '%20')
        .replace('\\', '/')
    )


class HTMLRenderer:
    def __init__(self):
        self._html_folder = Path(__file__).parent
        self._html_template = self._html_folder / 'render.html'

    def render(self, score: float, obs: str, exp: str):
        """
        Generate and open an HTML file showing a comparison between observed and expected values.
        """

        # Read the HTML template
        if not self._html_template.exists():
            raise FileNotFoundError(f"Template not found at {self._html_template}")

        template = self._html_template.read_text(encoding="utf-8")

        observed = ''
        for ol, el in zip(obs.splitlines(), exp.splitlines()):
            for ochar, echar in zip(ol, el):
                if ochar != echar:
                    observed += f'<span style="color: red;">{ochar}</span>'
                else:
                    observed += ochar
            observed += '<br>'

        expected = ''
        for el in exp.splitlines():
            expected += f'<span style="color: green;">{el}</span><br>'

        # Generate HTML content
        print(f'Observed: {observed}')
        print(f'Expected: {expected}')
        html_content = template.replace('%%OBSERVED%%', observed).replace('%%EXPECTED%%', expected)
        html_content = html_content.replace('%%SCORE%%', str(score))

        # Write final HTML to disk
        html_file = Path(os.getcwd()) / 'render.html'
        html_file.write_text(html_content, encoding='utf-8')

        # Open in browser
        url = f'file://{quote(str(html_file))}'
        print(f'Opening {url}')
        # webbrowser.open(url)
        return url


if __name__ == '__main__':
    renderer = HTMLRenderer()
    score, obs, exp = edit_dist('hello', 'hallo')
    renderer.render(score, obs, exp)