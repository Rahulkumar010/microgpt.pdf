---
layout: default
title: "MicroGPT.PDF"
description: "Training a neural network inside the Chrome PDF Sandbox."
---

# Training a Transformer Language Model... in a PDF?!

*Running machine learning models inside the Acrobat JavaScript Sandbox.*

PDFs are often treated as static, printed documents. But the PDF standard includes a JavaScript execution engine.

Inspired by [doompdf](https://github.com/ading2210/doompdf) (which runs DOOM inside a PDF) and [pdftris](https://github.com/ThomasRinsma/pdftris), I started exploring JS embedding in PDFs to see the limits of the browser's PDF engine. I decided to try porting Andrej Karpathy's minimalist Transformer implementation, [MicroGPT](https://gist.github.com/karpathy/8627fe009c40f57531cb18360106ce95), into a standalone PDF file.

You can view the code and generate your own on [GitHub](https://github.com/).

> **<a href="microgpt.pdf" target="_blank">try microgpt.pdf</a>**  
> *(Note: You must open this via GitHub Pages. GitHub's standard file viewer blocks the Javascript.)*

## The Acrobat JS Sandbox

Adobe implemented Acrobat JavaScript to support interactive forms and 3D rendering. Modern web browsers like Chrome and Firefox implement a sandboxed version of this API via their PDF rendering engines.

The sandbox removes access to the browser's DOM and blocks most network requests, but it leaves the core math and array manipulation capabilities of the V8 engine intact. With math and arrays, we can run backpropagation.

## Transpiling Python to ES5

PDFs don't natively support ES6 modules or advanced JavaScript syntax across all viewers. I had to manually transpile Karpathy's `MicroGPT` architecture into ES5-compatible JavaScript. 

This required:
1. Re-implementing the Autograd engine (the `Value` class).
2. Implementing the Box-Muller transformation for random Gaussian weights.
3. Translating the forward and backward passes of the Transformer architecture.

## Escaping the UI Freeze

Running a heavy computation loop in the browser freezes the UI thread. Normal web apps use Web Workers to avoid this, but PDFium doesn't support them. 

Running the training loop synchronously locked up the PDF for minutes at a time. The workaround was to compute gradients for 5 steps at a time, flush the text buffer to the PDF form field, and yield the thread using `setTimeout(trainStep, 10)`. This keeps the viewer responsive and provides a terminal-like auto-scrolling output inside the PDF.

## Bypassing Network Blocks

I wanted users to be able to paste a GitHub link to a raw text dataset. However, Chrome's PDF viewer treats PDFs opened via `file:///` as opaque origins. This causes an "Unsafe attempt to load URL" error if you attempt an XMLHttpRequest.

To work around this, the code dynamically rewrites `github.com/.../blob/...` URLs to their `raw.githubusercontent.com` equivalents and calls the native `fetch` API. Chrome sometimes exposes `fetch` to the PDF environment depending on security flags. If the request fails, the code catches the exception and prompts the user to paste the raw text instead.

## Wrapping Up

The output is a self-contained `microgpt.pdf` file. You double-click it, it opens in your web browser, and it trains a neural network locally without needing a Python environment. 

It shows what modern browser JavaScript engines can do, and serves as a reminder of how much unseen code runs inside everyday PDF files.
