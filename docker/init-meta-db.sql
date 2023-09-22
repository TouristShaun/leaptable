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

-- USER
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

create unique index user_email_uindex
    on "user" (email);

-- NAMESPACE_MEMBERSHIP
create table namespace_membership
(
    _id          uuid        default gen_random_uuid()           not null
        constraint namespace_membership_pk
            primary key,
    _cr          timestamp   default now(),
    _up          timestamp   default now(),
    namespace_id uuid                                            not null
        constraint namespace_membership_namespace__id_fk
            references namespace
            on delete cascade,
    user_id      uuid                                            not null
        constraint namespace_membership_user__id_fk
            references "user"
            on delete cascade,
    role         varchar(16) default 'MEMBER'::character varying not null
);

create unique index namespace_membership_user_namespace_idx
    on namespace_membership (user_id, namespace_id);



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
    namespace_id    uuid                                                       not null
        constraint dataframe_namespace__id_fk
            references namespace
            on delete cascade,
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

-- APP STATE
create table app_state
(
    meta       jsonb                    default '{}'::jsonb       not null,
    user_id    uuid                                               not null,
    session_id varchar(64)                                        not null,
    _id        uuid                     default gen_random_uuid() not null,
    _cr        timestamp with time zone default now()             not null,
    _up        timestamp with time zone default now()             not null
);

create unique index app_state__id_uindex
    on app_state (_id);

-- INVITE
create table invite
(
    _id           uuid                     default gen_random_uuid() not null
        constraint invite_pk
            primary key,
    _cr           timestamp with time zone default now()             not null,
    _up           timestamp with time zone default now()             not null,
    email         varchar(100)                                       not null,
    num_reminders integer                  default 0                 not null,
    accepted      boolean                  default false             not null,
    last_reminder timestamp with time zone,
    namespace_id  uuid                                               not null
        constraint invite_namespace__id_fk
            references namespace
            on delete cascade,
    inviter       uuid                                               not null
        constraint invite_user__id_fk
            references "user"
            on delete cascade,
    promo_name    varchar(50)
);

create unique index invitate__id_uindex
    on invite (_id);

-- HISTORY
create table history
(
    _id            uuid                     default gen_random_uuid()             not null
        constraint history_pk
            primary key,
    _cr            timestamp with time zone default now()                         not null,
    _up            timestamp with time zone default now()                         not null,
    type           varchar                  default 50                            not null,
    initiator_id   uuid                                                           not null,
    dataframe_id   varchar(100),
    item           jsonb                    default '{}'::jsonb                   not null,
    initiator_type varchar(15)              default 'user-web'::character varying not null,
    namespace_id   uuid                                                           not null,
    version        varchar(20)              default 'v0.01'::character varying,
    job_id         uuid
);

create unique index queries_id_uindex
    on history (_id);


