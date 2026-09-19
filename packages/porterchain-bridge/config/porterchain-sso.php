<?php

/**
 * PorterChain ↔ Fleetbase SSO bridge config.
 * Env vars are set on the Fleetbase application container.
 */
return [
    'sso' => [
        'jwt_secret' => env('PORTERCHAIN_SSO_JWT_SECRET', env('JWT_SECRET')),
        'issuer' => env('PORTERCHAIN_SSO_ISSUER', 'porterchain'),
        'audience' => env('PORTERCHAIN_SSO_AUDIENCE', 'fleetbase'),
    ],
    'fleetbase' => [
        'default_company_uuid' => env('PORTERCHAIN_FLEETBASE_DEFAULT_COMPANY_UUID'),
    ],
];
