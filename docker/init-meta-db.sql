-- Namespace
CREATE TABLE IF NOT EXISTS namespace
(
    _id             uuid                     default gen_random_uuid() not null
        constraint namespace_pk
            primary key,
    _cr             timestamp with time zone default now()             not null,
    _up             timestamp with time zone default now()             not null,
    slug            varchar(100)                                       not null
        unique,
    trace_db_params jsonb                    default '{}'::jsonb       not null,
    name            varchar(100)                                       not null,
    data_db_params  jsonb                    default '{}'::jsonb       not null,
    hasura_params       jsonb            default '{}'::jsonb
);

create unique index namespace__id_uindex
    on namespace (_id);

-- API Keys
CREATE TABLE IF NOT EXISTS api_key
(
    _id          uuid                     default gen_random_uuid() not null
        constraint api_key_pk
            primary key,
    _cr          timestamp with time zone default now()             not null,
    _up          timestamp with time zone default now()             not null,
    key          varchar(250)                                       not null,
    active       boolean                  default true              not null,
    namespace_id uuid                                               not null
        constraint api_key_namespace__id_fk
            references namespace
            on delete cascade,
    usage_count  bigint                   default 0                 not null,
    name         varchar(100)                                       not null
);

create unique index api_key__id_uindex
    on api_key (_id);

-- DATAFRAME
CREATE TABLE IF NOT EXISTS dataframe
(
    _id             uuid                     default gen_random_uuid()         not null
        constraint dataset_pkey
            primary key,
    _cr             timestamp with time zone default now()                     not null,
    _up             timestamp                default now()                     not null,
    name            varchar(64)                                                not null,
    slug            varchar(64)                                                not null,
    meta            jsonb                    default '{}'::jsonb,
    namespace_id    uuid                                                       not null
        constraint dataframe_namespace__id_fk
            references namespace
            on delete cascade,
    _blueprint      jsonb                    default '{}'::jsonb,
    bp_version      varchar(10)              default 'v0.1'::character varying not null,
    table_name      text,
    icon            varchar(20)              default '📘'::character varying
);

-- BLUEPRINT
CREATE TABLE IF NOT EXISTS blueprint
(
    _id              uuid                     default gen_random_uuid()         not null
        constraint blueprint_pk
            primary key,
    _cr              timestamp with time zone default now()                     not null,
    _up              timestamp with time zone default now()                     not null,
    display_name     varchar(100)                                               not null,
    display_format   varchar(50)              default 'TEXT'::character varying not null,
    dataframe_id     uuid                                                       not null
        constraint blueprint_dataframe__id_fk
            references dataframe
            on delete cascade,
    sticky_left      boolean                  default false                     not null,
    sticky_right     boolean                  default false                     not null,
    system           boolean                  default false                     not null,
    width            integer                  default 350                       not null,
    type             varchar(50)                                                not null,
    selected         boolean                  default false                     not null,
    ai_gen           boolean                  default false                     not null,
    shown            boolean                  default true                      not null,
    index            integer                  default 0                         not null,
    overflow         varchar(50)              default 'CLIP'::character varying not null,
    horizontal_align varchar(20)              default 'LEFT'::character varying not null,
    vertical_align   varchar(20)              default 'TOP'::character varying  not null,
    slug             varchar(200)                                               not null,
    is_processing    boolean                  default false                     not null
);

create unique index blueprint__id_uindex
    on blueprint (_id);

create unique index blueprint__dataframe_id_slug_uindex
    on blueprint (dataframe_id, slug);

-- auto-generated definition
CREATE TABLE IF NOT EXISTS "user"
(
    _id                 uuid                     default gen_random_uuid() not null
        constraint user_pk
            primary key,
    _cr                 timestamp with time zone default now()             not null,
    _up                 timestamp with time zone default now()             not null,
    email               varchar(100)                                       not null,
    name                varchar(100)                                       not null,
    picture             varchar(200)                                       not null,
    email_verified      boolean                  default false             not null,
    last_seen           timestamp with time zone
);

create unique index user__id_uindex
    on "user" (_id);