# Asteria

This is the Asteria monorepo. It contains:

- **Asteria** — the static site generator itself.
- **Odt2web** — the converter used by Asteria to generate HTML from ODT files.
- **Themes** — some themes to use with Asteria.

## Why ODT files?

After a discussion about SSGs on Mastodon, someone said something that hit really hard on my assumptions:

> "Even the easiest SSG is still too complicated for a regular writer. Markdown is, in theory, easy to learn, but it's still an entirely new syntax. Besides that, Markdown is very limited compared to rich text created in a standard text editor. In an ideal world, I can just write and format my texts in a text editor, drop the results into a folder, and the SSG handles the process of publishing the text in the right format as a web page."

And he was absolutely right. The hoops I have to jump through to get text in columns using Markdown simply aren't worth the effort, just to cite one example. So I decided to find out if it was possible to reliably use a rich text format as the basis for an SGG and, guess what? It was.

Since DOC/DOCX is a proprietary format, and trying to keep up with it through reverse engineering is stupid, while ODT is open and well documented and can even be produced by MS Office and Google Docs, it seemed like the way to go.

## Why one more SSG?

Well, the truth is I was planning to just create a plugin for MkDocs. But MkDocs was discontinued, and Zensical, its successor, isn't Python-based anymore.

I thought about writing a plugin for some other SSGs, but the task looked harder than just creating a new SSG focused exclusively on ODT files. This way, I have total control to make the necessary adjustments for this strategy to work correctly.

## Is there slop here?

Yes, a good chunk.

Most of the work on odt2web was done with Claude's assistance. Some other parts, such as TOC and Nav generation, were also made with its help.

## Can I open issues/PRs using slop?

Well, I would be a hypocrite if I said no, but it's a little more complicated than that.

The thing is: I used Claude to help me with the code, but **I KNOW THIS CODE DEEPLY**. I know what it does and doesn't do, where things are, and how to fix things in it **WITHOUT CLAUDE**.

If you understand what you're doing and use AI just to do brute-force/repetitive work, and you can answer questions and propose solutions yourself, then you can absolutely use it to work on this project.

If you use it like a magic black box and are incapable of understanding the results it produces, or are unable to write anything without it, then no, you can't use it to work on this project.

And I will read some minds right now. Some of you are thinking:

> "He won't know if I use it like a magic box or not."

Friend, I will.

It's very easy to tell when someone doesn't understand what they're doing with code. You just don't see it because **you don't understand what you're doing with code**, ahahah.

## But I don't like Slop...

No problem, just don't use the monorepo's content. Believe it or not, you aren't forced to. You can hate Slop all you want, as long as you don't come and hassle me about it. Asteria is a personal project for personal use. If you like it, you are welcome to use it too, but I will steer it in the direction I see fit.

## Current status

All components are in use. There are still some adjustments and minor bugs to fix, but all core features are already functional.

## How to install

In the future, both the SSG and the conversion library will be available on [PyPI](https://pypi.org/). However, since the project is currently under development, installation is still manual.

### 1. Clone the repository

```bash
git clone https://github.com/your-user/your-repository.git
cd your-repository
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate the virtual environment:

**Linux / macOS:**

```bash
source .venv/bin/activate
```

**Windows:**

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install the packages

With the virtual environment activated, install both the SSG and the ODT conversion library in editable mode:

```bash
pip install -e odt2web -e asteria
```

Using editable mode (`-e`) means that changes made to the source code are immediately available without reinstalling the packages.

