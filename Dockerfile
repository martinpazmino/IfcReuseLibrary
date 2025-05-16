FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    curl \
    unzip \
    libocct-data-exchange-dev \
    libocct-ocaf-dev \
    libocct-visualization-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --branch v0.7.0 --recursive https://github.com/IfcOpenShell/IfcOpenShell.git /ifcopenshell

WORKDIR /ifcopenshell
RUN mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release ../cmake && \
    make -j$(nproc) && make install

RUN pip install trimesh numpy
