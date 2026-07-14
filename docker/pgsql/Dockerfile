FROM pgvector/pgvector:pg16

# 1. 安装编译依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    postgresql-server-dev-16 \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/jaiminpan/pg_jieba.git /tmp/pg_jieba \
    && cd /tmp/pg_jieba \
    && git submodule update --init --recursive \
    && mkdir build \
    && cd build \
    && cmake \
        -DCMAKE_INSTALL_PREFIX=/usr/lib/postgresql/16 \
        -DPostgreSQL_TYPE_INCLUDE_DIR=/usr/include/postgresql/16/server \
        -DPostgreSQL_INCLUDE_DIR=/usr/include/postgresql/16/server \
        -DPG_CONFIG=/usr/lib/postgresql/16/bin/pg_config \
        .. \
    && make -j$(nproc) \
    && make install \
    && rm -rf /tmp/pg_jieba

# 3. 可选：让 pg_jieba 随数据库启动加载（性能更好）
RUN echo "shared_preload_libraries = 'pg_jieba'" \
    >> /usr/share/postgresql/16/postgresql.conf.sample