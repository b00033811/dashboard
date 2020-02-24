FROM python:3.5-stretch AS build-env
WORKDIR /usr/src/app
COPY requirements.txt .
COPY app.py .
RUN pip install --upgrade pip --upgrade setuptools && \
    pip install -r requirements.txt  && \
    pyinstaller app.py --hidden-import pkg_resources.py2_warn --hidden-import pandas
RUN echo "Installed bokeh dashboard"
RUN echo "Copying into a distroless container"
FROM gcr.io/distroless/python3
COPY --from=build-env /usr/src/app/dist /usr/src/app/dist
ENTRYPOINT ["/usr/src/app/dist/app/app"]
