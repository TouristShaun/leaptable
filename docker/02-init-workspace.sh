#!/bin/bash
set -e

curl ident.me

HASURA_GRAPHQL_ADMIN_SECRET=reframe

printf "\nCreating default namespace\n"
SKEY=`curl --location 'http://api:8000/api/v1/namespace/' \
--header 'Content-Type: application/json' \
--data '{
    "slug": "default",
    "name": "Default"
}' | jq -r .data.api_key`

printf "\nCreating default user\n"

curl --location 'http://api:8000/api/v1/user/' \
--header "X-API-KEY: ${SKEY}" \
--header 'Content-Type: application/json' \
--data-raw '{
    "name": "reframe",
    "email": "user@reframe.is"
}'

# Create the Reframe Meta Connection
printf "\nCreating Hasura connection 'Reframe | Meta'"

curl --location 'http://hasura:8080/v1/metadata' \
--header "x-hasura-admin-secret: ${HASURA_GRAPHQL_ADMIN_SECRET}" \
--header 'Content-Type: application/json' \
--data '{
  "type": "pg_add_source",
  "args": {
    "name": "Reframe | Meta",
    "configuration": {
      "connection_info": {
        "database_url": {
           "from_env": "HASURA_GRAPHQL_REFRAME_METADB_URL"
         },
        "pool_settings": {
          "max_connections": 50,
          "idle_timeout": 180,
          "retries": 1,
          "pool_timeout": 360,
          "connection_lifetime": 600
        },
        "use_prepared_statements": true,
        "isolation_level": "read-committed"
      }
    },
    "replace_configuration": true
  }
}'

curl --location 'http://hasura:8080/v1/metadata' \
--header "x-hasura-admin-secret: ${HASURA_GRAPHQL_ADMIN_SECRET}" \
--header 'Content-Type: application/json' \
--data '{
    "type" : "pg_track_table",
    "args" : {
        "source": "Reframe | Meta",
        "table": {
            "name": "namespace",
            "schema": "public"
        }
    }
}'

curl --location 'http://hasura:8080/v1/metadata' \
--header "x-hasura-admin-secret: ${HASURA_GRAPHQL_ADMIN_SECRET}" \
--header 'Content-Type: application/json' \
--data '{
    "type" : "pg_track_table",
    "args" : {
        "source": "Reframe | Meta",
        "table": {
            "name": "user",
            "schema": "public"
        }
    }
}'

echo
curl --location 'http://hasura:8080/v1/metadata' \
--header "x-hasura-admin-secret: ${HASURA_GRAPHQL_ADMIN_SECRET}" \
--header 'Content-Type: application/json' \
--data '{
    "type" : "pg_track_table",
    "args" : {
        "source": "Reframe | Meta",
        "table": {
            "name": "namespace_membership",
            "schema": "public"
        }
    }
}'

echo
curl --location 'http://hasura:8080/v1/metadata' \
--header "x-hasura-admin-secret: ${HASURA_GRAPHQL_ADMIN_SECRET}" \
--header 'Content-Type: application/json' \
--data '{
    "type" : "pg_track_table",
    "args" : {
        "source": "Reframe | Meta",
        "table": {
            "name": "dataframe",
            "schema": "public"
        }
    }
}'

echo
curl --location 'http://hasura:8080/v1/metadata' \
--header "x-hasura-admin-secret: ${HASURA_GRAPHQL_ADMIN_SECRET}" \
--header 'Content-Type: application/json' \
--data '{
    "type" : "pg_track_table",
    "args" : {
        "source": "Reframe | Meta",
        "table": {
            "name": "blueprint",
            "schema": "public"
        }
    }
}'

echo
curl --location 'http://hasura:8080/v1/metadata' \
--header "x-hasura-admin-secret: ${HASURA_GRAPHQL_ADMIN_SECRET}" \
--header 'Content-Type: application/json' \
--data '{
    "type" : "pg_track_table",
    "args" : {
        "source": "Reframe | Meta",
        "table": {
            "name": "app_state",
            "schema": "public"
        }
    }
}'

echo
curl --location 'http://hasura:8080/v1/metadata' \
--header "x-hasura-admin-secret: ${HASURA_GRAPHQL_ADMIN_SECRET}" \
--header 'Content-Type: application/json' \
--data '{
    "type" : "pg_track_table",
    "args" : {
        "source": "Reframe | Meta",
        "table": {
            "name": "history",
            "schema": "public"
        }
    }
}'

echo
curl --location 'http://hasura:8080/v1/metadata' \
--header "x-hasura-admin-secret: ${HASURA_GRAPHQL_ADMIN_SECRET}" \
--header 'Content-Type: application/json' \
--data '{
    "type" : "pg_track_table",
    "args" : {
        "source": "Reframe | Meta",
        "table": {
            "name": "invite",
            "schema": "public"
        }
    }
}'

echo
curl --location 'http://hasura:8080/v1/metadata' \
--header "x-hasura-admin-secret: ${HASURA_GRAPHQL_ADMIN_SECRET}" \
--header 'Content-Type: application/json' \
--data '{
    "type" : "pg_track_table",
    "args" : {
        "source": "Reframe | Meta",
        "table": {
            "name": "api_key",
            "schema": "public"
        }
    }
}'

echo
curl --location 'http://hasura:8080/v1/metadata' \
--header "x-hasura-admin-secret: ${HASURA_GRAPHQL_ADMIN_SECRET}" \
--header 'Content-Type: application/json' \
--data '{
    "type" : "pg_create_object_relationship",
    "args": {
        "table": "namespace_membership",
        "name": "namespace",
        "source": "Reframe | Meta",
        "using": {
            "foreign_key_constraint_on" : ["namespace_id"]
        }
    }
}'

echo
curl --location 'http://hasura:8080/v1/metadata' \
--header "x-hasura-admin-secret: ${HASURA_GRAPHQL_ADMIN_SECRET}" \
--header 'Content-Type: application/json' \
--data '{
    "type" : "pg_create_object_relationship",
    "args": {
        "table": "namespace_membership",
        "name": "user",
        "source": "Reframe | Meta",
        "using": {
            "foreign_key_constraint_on" : ["user_id"]
        }
    }
}'

echo
curl --location 'http://hasura:8080/v1/metadata' \
--header "x-hasura-admin-secret: ${HASURA_GRAPHQL_ADMIN_SECRET}" \
--header 'Content-Type: application/json' \
--data '{
    "type" : "pg_create_object_relationship",
    "args": {
        "table": "user",
        "name": "namespace_membership",
        "source": "Reframe | Meta",
        "using": {
            "foreign_key_constraint_on" : {
                "table" : "namespace_membership",
                "columns" : ["user_id"]
            }
        }
    }
}'

echo
curl --location 'http://hasura:8080/v1/metadata' \
--header "x-hasura-admin-secret: ${HASURA_GRAPHQL_ADMIN_SECRET}" \
--header 'Content-Type: application/json' \
--data '{
    "type" : "pg_create_object_relationship",
    "args": {
        "table": "dataframe",
        "name": "namespace",
        "source": "Reframe | Meta",
        "using": {
            "foreign_key_constraint_on" : ["namespace_id"]
        }
    }
}'

echo
curl --location 'http://hasura:8080/v1/metadata' \
--header "x-hasura-admin-secret: ${HASURA_GRAPHQL_ADMIN_SECRET}" \
--header 'Content-Type: application/json' \
--data '{
    "type" : "pg_create_array_relationship",
    "args": {
        "table": "dataframe",
        "name": "blueprint_list",
        "source": "Reframe | Meta",
        "using": {
            "foreign_key_constraint_on" : {
                "table" : "blueprint",
                "columns" : ["dataframe_id"]
            }
        }
    }
}'

wget -O "Sample | Techstars Companies.xlsx" https://git.reframe.is/sample-dataset.xslx

# Upload the sample file.
SAMPLE_FILE="Sample | Techstars Companies.xlsx"
SAMPLE_FILE_TYPE="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
curl --location 'http://api:8000/api/v1/dataframe/upload/' \
  -X POST \
  -F "file=@$SAMPLE_FILE;type=$SAMPLE_FILE_TYPE" \
  --header "X-API-KEY: ${SKEY}" \
  --header "Content-Type: multipart/form-data"