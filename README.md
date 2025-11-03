## AI Money

This is a personal finance expense tracker. This works on top of transactions in [beancount](https://beancount.github.io/) file format.
The app converts uploaded credit card statements (CSV or PDF) into a beancount file and categorizes the expenses with an AI agent.

### Features
- **Upload PDF or CSV statements** - Supports any credit card statement format
- **AI-powered PDF parsing** - Automatically extracts transactions from PDF statements using Claude AI
- **Smart categorization** - Categorize transactions using AI
- **Multi-currency support** - Handles transactions in different currencies

![AI money categorize demo](ai-money-categorize.png)

### Setup

#### Backend
- Install the python version specified in pyproject.toml
- cd backend
- pip install poetry
- poetry install

#### Frontend
This is a [Next.js](https://nextjs.org) app bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

Install
- Node.js (version 22.x or later recommended)
- npm (comes with Node.js)
- cd frontend
- npm install

### Run

**Backend**

## To build and run the application:

1. Install dependencies:
```bash
cd backend
poetry shell
poetry install
```

2. Run the server:
```bash
ANTHROPIC_API_KEY=<your_key> poetry run uvicorn app:app --reload
```

## Build and run the application using Docker:

Build the Docker image:
```bash
docker build -t ai-money/backend .
```

Test locally:
```bash
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=your_key ai-money/backend
```

### AWS Deployment

```
docker build --platform=linux/amd64 -t ai-money/backend:`git log -n 1 --format="%H"` .
docker tag ai-money/backend:`git log -n 1 --format="%H"` 867344451303.dkr.ecr.us-west-2.amazonaws.com/ai-money/backend:`git log -n 1 --format="%H"`
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 867344451303.dkr.ecr.us-west-2.amazonaws.com
docker push 867344451303.dkr.ecr.us-west-2.amazonaws.com/ai-money/backend:`git log -n 1 --format="%H"`
```


**Frontend**

## To build and run the application:
```
cd frontend
npm run dev
```

And visit localhost:3000


## Build and run the application using Docker:

```bash
# Build the Docker image
docker build -t ai-money/frontend .

# Run the container
docker run -p 3000:3000 -e BACKEND_HOST=localhost:8000 ai-money/frontend
```

### AWS Deployment

```
docker build --platform=linux/amd64 -t ai-money/frontend:`git log -n 1 --format="%H"` .
docker tag ai-money/frontend:`git log -n 1 --format="%H"`  867344451303.dkr.ecr.us-west-2.amazonaws.com/ai-money/frontend:`git log -n 1 --format="%H"`
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 867344451303.dkr.ecr.us-west-2.amazonaws.com
docker push 867344451303.dkr.ecr.us-west-2.amazonaws.com/ai-money/frontend:`git log -n 1 --format="%H"`
```




**Supported Statement Formats**

The application now supports **both CSV and PDF** credit card statements:

- **CSV**: Sample CSV statement available in `backend/statements/sample-statement.csv`
- **PDF**:
  - The AI automatically extracts transactions from any credit card PDF statement format
  - No manual conversion needed!

Simply upload your credit card statement (CSV or PDF) through the web interface, and the app will automatically process it.


### Dashboard

[Paisa](https://paisa.fyi/) is a dashboard tool to visualize the transactions. To visualiase the transactions you can use that.
