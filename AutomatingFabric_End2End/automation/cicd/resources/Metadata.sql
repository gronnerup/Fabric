IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='landing_to_base' AND xtype='U')
BEGIN
    CREATE TABLE landing_to_base (
        id INT IDENTITY(1,1) PRIMARY KEY,
        source NVARCHAR(250) NOT NULL,
        format NVARCHAR(50) NOT NULL,
        destination NVARCHAR(250) NOT NULL,
        projected_columns NVARCHAR(1000) NULL
    );
END;

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='notebook_orchestrator' AND xtype='U')
BEGIN
    CREATE TABLE [dbo].[notebook_orchestrator](
        [id] [int] IDENTITY(1,1) PRIMARY KEY,
        [notebook_name] [nvarchar](250) NOT NULL,
        [notebook_path] [nvarchar](250) NOT NULL,
        [cell_timeout] int NOT NULL DEFAULT 90,
        [retry_count] int NOT NULL DEFAULT 1,
        [retry_interval] int NOT NULL DEFAULT 10,
        [arguments] [nvarchar](1000) NOT NULL DEFAULT '{"useRootDefaultLakehouse": true}',
        [dependencies] [nvarchar](1000) NULL,
        [group] [nvarchar](250) NOT NULL DEFAULT 'default',
        [is_enabled] bit NOT NULL DEFAULT 1
    );
END;

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='source_ingest_conn' AND xtype='U')
BEGIN
    CREATE TABLE [dbo].[source_ingest_conn](
        [id] [int] IDENTITY(1,1) PRIMARY KEY,
        [connection_id] [nvarchar](50) NOT NULL,
        [connection_name] [nvarchar](250) NOT NULL,
        [connection_type] [nvarchar](250) NOT NULL,
        [is_enabled] bit NOT NULL DEFAULT 1
    );
END;

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='source_ingest_obj' AND xtype='U')
BEGIN
    CREATE TABLE [dbo].[source_ingest_obj](
        [id] [int] IDENTITY(1,1) PRIMARY KEY,
        [connection_id] INT NOT NULL,
        [schema_name] [nvarchar](250) NOT NULL,
        [table_name] [nvarchar](250) NOT NULL,
        [is_enabled] bit NOT NULL DEFAULT 1
    );
END;