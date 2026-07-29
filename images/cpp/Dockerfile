FROM gcc:9

RUN useradd -m -u 1001 -s /bin/bash sandboxuser

RUN mkdir -p /code && chown sandboxuser:sandboxuser /code


WORKDIR /code

USER sandboxuser