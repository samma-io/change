FROM mcr.microsoft.com/playwright:v1.59.1-jammy

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /code

COPY code/ /code/

RUN npm ci --omit=dev

RUN mkdir /out

CMD ["node", "scan.js"]
