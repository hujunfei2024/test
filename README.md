# ChatGPT Academic Optimizer

A simple web interface for academic research and experimentation using GPT-3.5.

This is the forked version from [the project](https://github.com/binary-husky/chatgpt_academic)

**If you like this project, please give it a star. If you have come up with more useful academic shortcuts, feel free to open an issue or pull request.**

## Features

- Automatic paper abstract generation based on a provided LaTeX file
- Automatic code summarization and documentation generation
- C++ project header file analysis
- Python project analysis
- Self-code interpretation and dissection
- Experimental function template

<div align="center">

| Function                                  | Description                                                                                      |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------ |
| One-click polishing                       | Supports one-click polishing and finding grammar errors in papers                                |
| One-click Chinese-English translation     | One-click Chinese-English translation                                                            |
| One-click code interpretation             | Can display code correctly and interpret code                                                    |
| Custom shortcut keys                      | Supports custom shortcut keys                                                                    |
| Configure proxy server                    | Supports configuring proxy server                                                                |
| Modular design                            | Supports customizable high-order experimental functions                                          |
| Self-program analysis                     | [Experimental feature] One-click to understand the source code of this project                   |
| Program analysis                          | [Experimental feature] One-click to analyze other Python/C++ projects                            |
| Reading papers                            | [Experimental feature] One-click to read the full text of a latex paper and generate an abstract |
| Batch comment generation                  | [Experimental feature] One-click to generate function comments in batches                        |
| chat analysis report generation           | [Experimental feature] Automatically generates summary reports after running                     |
| Formula display                           | Can display the tex form and rendering form of the formula at the same time                      |
| Image display                             | Can display images in markdown                                                                   |
| Supports markdown tables generated by GPT | Supports markdown tables generated by GPT                                                        |

</div>

- New interface
<div align="center">
<img src="https://user-images.githubusercontent.com/96192199/227528413-36ab42da-d589-4ef1-ba75-28aa02442d05.png" width="700" >
</div>

- All buttons are dynamically generated by reading functional.py, and custom functions can be freely added to free the clipboard
<div align="center">
<img src="img/eq.gif" width="700" >
</div>

- Code display is also natural https://www.bilibili.com/video/BV1F24y147PD/
<div align="center">
<img src="img/polish.gif" width="700" >
</div>

- Supports markdown tables generated by GPT
<div align="center">
<img src="img/demo2.jpg" width="500" >
</div>

- If the output contains formulas, it will be displayed in both tex and rendering forms at the same time for easy copying and reading
<div align="center">
<img src="img/demo.jpg" width="500" >
</div>

- Too lazy to look at the project code? Just show off the chatgpt mouth
<div align="center">
<img src="https://user-images.githubusercontent.com/96192199/226935232-6b6a73ce-8900-4aee-93f9-733c7e6fef53.png" width="700" >
</div>

## Usage

### Prerequisites

- OpenAI API key (can be obtained from [here](https://beta.openai.com/signup/))
- Python 3.9 or higher

### Setup

```console
$pip install academic-chatgpt
```

### Run

1. Set your OpenAI API key and other configurations in `chataca.toml` or
   `~/.config/chataca/chataca.toml`

The configuration file will locate at current working directory or `~/.config/chataca/`.
The example of `chataca.toml`

```toml
API_KEY = "sk-zH**********************************************"
API_URL = "https://api.openai.com/v1/chat/completions"
USE_PROXY = false
TIMEOUT_SECONDS = 30
WEB_PORT = 8080
MAX_RETRY = 3
LLM_MODEL = "gpt-3.5-turbo"
```

If you are in China, you need to set up an overseas agent to use the OpenAI API.

2. Start the server: `chataca`

### Experimental features

#### C++ project header file analysis

In the `project path` area, enter the project path and click on "[Experimental] Analyze entire C++ project (input the root directory of the project)

#### LaTeX project abstract generation

In the `project path` area, enter the project path and click on "[Experimental] Read LaTeX paper and write abstract (input the root directory of the project)

#### Python project analysis

In the `project path` area, enter the project path and click on "[Experimental] Analyze entire Python project (input the root directory of the project)"
