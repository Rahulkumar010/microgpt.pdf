# MicroGPT.PDF

> **<a href="microgpt.pdf" target="_blank">try microgpt.pdf</a>**  
> *(Note: The browser's native PDF viewer will run the Javascript. GitHub's built-in repo viewer will not.)* 

This is a PDF file that trains a Transformer language model locally in the PDF viewer's JavaScript sandbox. It requires no servers or external APIs.

> [!NOTE]
> The entire neural network training loop (forward pass, backward pass, gradient descent) runs locally in your browser or PDF viewer.

## Background: JavaScript in a PDF
PDFs support an interactive scripting layer called Acrobat JS. Modern browsers (like Chrome via PDFium) implement a sandbox for this standard.

The sandbox restricts DOM access and cross-origin network requests, but it supports floating-point math, array manipulation, and timers. That's enough to run a Transformer.

## How it Works
1. **The Model:** I transpiled Karpathy's pure Python [MicroGPT](https://gist.github.com/karpathy/8627fe009c40f57531cb18360106ce95) and some JavaScript reference implementations into standalone ES5 JavaScript. This includes an autograd engine (`Value` class), the Transformer architecture, and Box-Muller Gaussian weight initializations.
2. **The UI:** The Javascript execution context is bound to interactive AcroForm fields (buttons and text boxes).
3. **Execution Limits:** Running the training loop synchronously would freeze the browser UI thread. To fix this, the training runs in an asynchronous chunked loop that yields to `setTimeout`, streaming the loss outputs into the PDF text box.
4. **Dataset Fetching:** The script detects GitHub `blob` URLs in the dataset input box and converts them to `raw.githubusercontent.com` URLs to attempt a `fetch`. If the sandbox blocks the network request, it asks the user to paste the raw text directly.

## Build Instructions
This project uses `uv` for lightning-fast dependency management.

1. Clone this repository.
2. Install `uv` if you haven't already.
3. Run the following commands:
```bash
uv sync
uv run build_pdf.py [optional_dataset.txt]
```

The script generates `microgpt.pdf` in the root directory.

## Credits
- **MicroGPT Architecture:** [Andrej Karpathy](https://gist.github.com/karpathy/8627fe009c40f57531cb18360106ce95)
- **Inspiration:** Inspired by [doompdf](https://github.com/ading2210/doompdf) and [pdftris](https://github.com/ThomasRinsma/pdftris).

## License
This repository is licensed under the GNU GPL v3.

```
Rahul Kumar/microgpt.pdf - MicroGPT running inside a PDF file
Copyright (C) 2026 Rahul Kumar

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```
