# What the site needs to run, and nothing that is read from a provider console.
# That is what keeps the host reversible → docs/deploiement.md.
#
# The build platform is not this machine's:
#
#     docker build --platform linux/amd64 -t weather-simulator .
#
# Pinned to 3.13 rather than the 3.14 of the development venv. pyproject asks
# for >= 3.11 and nothing here is version-specific; 3.13 is the version whose
# wheels are certain for uvicorn's compiled extras. Revisit once a build has
# actually proved 3.14.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# The dependency list is read from pyproject.toml and never restated here. A
# second copy of it would drift from the first, and this one would drift
# silently: the image would still build.
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

# After the install, so that editing a page rebuilds one layer and not the
# environment.
COPY web/ ./web/

# ``-e`` above is not a convenience, and this line is why it is asserted rather
# than commented. app.py finds the pages by walking up from its own file
# (``parents[3] / "web"``), which lands on /app only while the package stays
# under src/. A regular install moves it into site-packages, where that walk
# lands elsewhere: mount_web finds no directory, returns False, and the server
# starts perfectly, answers the API normally, and serves 404 on /. Nothing in
# the logs says so. The build fails here instead.
RUN python -c "from weather_simulator.api.app import WEB; assert (WEB / 'pages' / 'home.html').is_file(), f'pages not found at {WEB}'"

RUN useradd --create-home --uid 1000 app
USER app

# The platform names the port. The image reads it and does not choose it.
ENV PORT=8080
EXPOSE 8080

# exec, so that uvicorn is PID 1 and takes the stop signal itself. An instance
# scaled back to zero should close its connections rather than be killed.
CMD ["sh", "-c", "exec uvicorn weather_simulator.api.app:app --host 0.0.0.0 --port ${PORT}"]
