FROM python:3.9

LABEL maintainer="ICT - ISS L3 AI <gva_ict_iss_l3_ai@icrc.org>"

# Install utilities and official MSSQL linux driver
# https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server?view=sql-server-ver15#debian17
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 mssql-tools libgssapi-krb5-2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ./requirements.txt /app/
RUN pip config set global.index-url https://packtest.gva.icrc.priv/pypi/AI_Python_TEST/simple && \
    pip config set global.trusted-host packtest.gva.icrc.priv && \
    pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    useradd samra
USER samra

COPY . /app/

ENTRYPOINT [ "/app/entrypoint.sh" ]