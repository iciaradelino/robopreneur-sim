# use official lightweight python image
FROM python:3.11-slim

# system deps: libgomp for numerical libs, libgeos for shapely fallback
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# set working directory
WORKDIR /app

# install python dependencies before copying source (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy source code
COPY . .

# solara runs on port 8765 by default
EXPOSE 8765

# default: run the interactive solara visualisation
# override for headless: docker run <image> python scripts/run_experiment.py <config_path>
CMD ["solara", "run", "app.py", "--host", "0.0.0.0", "--port", "8765"]
