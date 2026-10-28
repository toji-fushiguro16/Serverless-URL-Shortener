# Serverless URL Shortener

A serverless URL shortener built with Amazon API Gateway, AWS Lambda, and DynamoDB. The API creates short links and redirects visitors to the saved destination. AWS SAM defines the infrastructure and deployment.

## Features

- `POST /shorten` validates an HTTP/HTTPS URL and returns a short link.
- `GET /{code}` looks up a code and responds with an HTTP 302 redirect.
- DynamoDB uses on-demand billing and server-side encryption.
- Lambda receives least-privilege access to its link table through a SAM policy.
- `GET /health` provides a simple service health response.

## Architecture

```text
Client → API Gateway HTTP API → Lambda → DynamoDB
                   └────────────── redirect response (302)
```

## Deploy to AWS

Prerequisites: an AWS account, AWS CLI credentials configured for your account, Docker, and the AWS SAM CLI.

From this project directory:

```bash
sam build
sam deploy --guided
```

During guided deployment, choose a stack name and AWS region, and allow SAM to create the deployment role. After deployment, copy the `ApiUrl` output.

## Try the API

Create a short link (replace `API_URL`):

```bash
curl -X POST "$API_URL/shorten" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.example.com/docs"}'
```

The response includes a `short_url`, for example `https://abc.execute-api.ap-south-1.amazonaws.com/XyZ12_aB`. Open that link to receive a redirect. Check service health with:

```bash
curl "$API_URL/health"
```

## Project files

- `template.yaml` — API Gateway, Lambda, DynamoDB table, and scoped IAM policy.
- `src/app.py` — request validation, code creation, DynamoDB reads/writes, and redirects.

## Cleanup

The DynamoDB table has a retain policy to protect saved links. To remove the stack, first back up or delete the table and its data intentionally, then run `sam delete`.

## Learning outcomes and limitations

This project demonstrates serverless compute, managed HTTP APIs, NoSQL key-value storage, and infrastructure as code. It is a classroom project: it has no user accounts, abuse throttling, custom domains, or analytics. Add AWS WAF/rate limits and authentication before using it for public production traffic.
