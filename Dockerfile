# Use the official .NET 8 SDK image for building
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build

WORKDIR /app

# Copy csproj and restore dependencies
COPY src/GameServer/*.csproj ./src/GameServer/
RUN dotnet restore src/GameServer/GameServer.csproj

# Copy everything else and build
COPY . .
WORKDIR /app/src/GameServer
RUN dotnet build GameServer.csproj -c Release -o /app/build

# Publish the application
RUN dotnet publish GameServer.csproj -c Release -o /app/publish

# Use the official .NET 8 runtime image
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime

WORKDIR /app

# Install curl for health checks and grpcurl for debugging
RUN apt-get update && \
    apt-get install -y curl && \
    GRPCURL_VERSION="1.9.1" && \
    curl -sL "https://github.com/fullstorydev/grpcurl/releases/download/v${GRPCURL_VERSION}/grpcurl_${GRPCURL_VERSION}_linux_x86_64.tar.gz" | tar -xz && \
    mv grpcurl /usr/local/bin/ && \
    rm -f LICENSE README.md && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create directory for logs
RUN mkdir -p /app/logs

# Copy the published application
COPY --from=build /app/publish .

# Create a non-root user
RUN addgroup --system --gid 1001 gameserver && \
    adduser --system --uid 1001 --gid 1001 gameserver

# Change ownership of app directory
RUN chown -R gameserver:gameserver /app

# Switch to non-root user
USER gameserver

# Expose the gRPC and Health Check ports
EXPOSE 5001
EXPOSE 5002

# Set environment variables
ENV ASPNETCORE_ENVIRONMENT=Production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5002/health || exit 1

# Start the application
ENTRYPOINT ["dotnet", "GameServer.dll"]
