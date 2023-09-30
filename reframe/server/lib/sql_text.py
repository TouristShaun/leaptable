CREATE_TABLE_TRACE = """
CREATE TABLE trace.{table_name} (
    _id             uuid                            default gen_random_uuid()   not null    constraint {table_name}_pk primary key,
    _cr             timestamp   with time zone      default now()               not null,
    _up             timestamp   with time zone      default now()               not null,
    parent_id       uuid,
    entry           jsonb   not null,
    level           varchar(10) not null,
    job_id          uuid,
    correlation_id  uuid
);

CREATE INDEX {table_name}_id_idx ON trace.{table_name} (_id);
"""

CREATE_TABLE_JOB = """
CREATE TABLE trace.{table_name} (
    _id             uuid                            default gen_random_uuid()   not null    constraint {table_name}_pk primary key,
    _cr             timestamp   with time zone      default now()               not null,
    _up             timestamp   with time zone      default now()               not null,
    prompt                jsonb                                                         not null,
    prompt_format_version varchar(50)                                                   not null,
    initiator_id          uuid                                                          not null,
    initiator_type        varchar(25)                                                   not null,
    engine_vs             varchar(50)              default 'v0.0.01'::character varying not null,
    read_cache            boolean                  default true                         not null,
    write_cache           boolean                  default true                         not null,
    table_name              varchar(200)    not null,
    input_params            jsonb           not null,
    output_params           jsonb           not null
);

CREATE INDEX {table_name}_id_idx ON trace.{table_name} (_id);
"""

CREATE_TABLE_THREAD = """
CREATE TABLE trace.{table_name} (
    _id             uuid                            default gen_random_uuid()   not null    constraint {table_name}_pk primary key,
    _cr             timestamp   with time zone      default now()               not null,
    _up             timestamp   with time zone      default now()               not null,
    elem_id          uuid,
    group_id          uuid,
    dataframe_id          uuid,
    column_id          uuid
);

CREATE INDEX {table_name}_id_idx ON trace.{table_name} (_id);
"""

CREATE_TABLE_AGENT = """
CREATE TABLE {table_name} (
    _id             uuid                            default gen_random_uuid()   not null    constraint {table_name}_pk primary key,
    _cr             timestamp   with time zone      default now()               not null,
    _up             timestamp   with time zone      default now()               not null,
    name                varchar(50)                                             not null,
    slug                varchar(50)                                             not null unique,
    engine_vs             varchar(50)              default 'v0.0.01'::character varying not null,
    read_cache            boolean                  default true                         not null,
    write_cache           boolean                  default true                         not null
);

CREATE INDEX {table_name}_id_idx ON {table_name} (_id);
"""

CREATE_TABLE_TOOL = """
CREATE TABLE {table_name} (
    _id             uuid                            default gen_random_uuid()   not null    constraint {table_name}_pk primary key,
    _cr             timestamp   with time zone      default now()               not null,
    _up             timestamp   with time zone      default now()               not null,
    name                varchar(50)                                             not null,
    slug                varchar(50)                                             not null unique,
    engine_vs             varchar(50)              default 'v0.0.01'::character varying not null,
    read_cache            boolean                  default true                         not null,
    write_cache           boolean                  default true                         not null
);

CREATE INDEX {table_name}_id_idx ON {table_name} (_id);
"""