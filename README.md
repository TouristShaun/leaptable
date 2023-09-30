[![Watch the video](https://img.youtube.com/vi/M860LUfwiQc/maxresdefault.jpg)](https://youtu.be/M860LUfwiQc)

## About


Reframe is an experimental agent framework powered by GPT-4 that operates on dataframes.

Reframe unleashes the future with AI Agents that work for you. These virtual assistants automate workflows,
search the web, explore LinkedIn, and more - with human-like intelligence but without human limitations.
Reframe combines an effortless a low-code database, dozens of tireless AI agents and powerful Language Models like
GPT, so you can manage data smarter, not harder. Let AI Agents do the work so you can focus on insights.




[Installation](#installation) |  [Quick Start](#quick-start) | [Documentation](#documentation)

## Installation

```shell
curl -fsSL https://git.reframe.co/dc-install.sh | sh
```

By far the easiest way to install the ReframeAI server is to use docker.

```bash
wget https://git.reframe.is/docker-compose.yaml \
    https://git.reframe.is/.env.local \
    https://git.reframe.is/01-init.sh \
    https://git.reframe.is/02-init-workspace.sh \
    https://git.reframe.is/init-meta-db.sql

# Populate .env.local with values accordingly.
# .env.local

mkdir -p ~/.reframe/postgresql

docker compose -p reframe up -d
```

Shut down the service stack.
```bash
docker compose -p reframe down --volumes
```

Slack: https://reframe.slack.com

### Install docker compose stack client
```shell
pip install reframe
```

## Reframe strives to be

* 🥽 Transparent - through logging, and metrics that create visibility into the inner operations.
* 🤸🏾 Flexible - AI Agents and tools are independent of each other, allowing you to create workflows easily.
* 🧩 Composable. Reframe are simply executable python functions and classes with a well defined interface. You can easily construct sophisticated agents from basic building blocks. These building blocks can be obtained from our ecosystem or you can develop custom ones that are specific to your organization.
* 🛹 Incrementally adoptable - By using existing technologies such as Docker, Kubernetes and Celery Aigent enables you to seamlessly adopt it with your organization. From simple ZeroShot agents to sophisticated multi-step AI agents each component can be integrated into your existing workflows.
* 🔨 Reusable - once a tool is running, it can be utilized by various agents, thereby reducing operational overhead, increasing throughput and making tools easy to reason about.
* 🏎️ Fast by taking advantage of data parallelism and prompt sequencing in a manner increases efficiency and reduces the overall number of expensive API calls made to LLM endpoints.
* 🏟️ Rich ecosystem that enables your to pick and choose which tools and agents to deploy. Through contributions from open source developers, we are making great progress to develop a robust ecosystem of tools so that you always have a tool for the job.

# Features
* 🌐 Internet access for searches and information gathering
* 📥 Long-term and short-term memory management 
* 🧠 GPT-4 & Anthropic instances for text generation 
* 🔗 Access to popular websites and platforms 
* 🗃️ File storage and summarization with GPT-3.5 
* 🔌 Extensibility with Plugins

Running on a VM.

```shell
ssh -i ~/.ssh/key.pem -N -f -L 48080:localhost:48080 \
    -L 43001:localhost:43001 -L 43000:localhost:430000 \
    user@x.x.x.x
```

## Documentation
More documentation is available here: [https://reframe.co/docs](https://to.reframe.co/docs)