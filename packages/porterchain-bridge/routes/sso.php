<?php

use Illuminate\Support\Facades\Route;
use Porterchain\FleetbaseBridge\Http\Controllers\SsoController;

/*
|--------------------------------------------------------------------------
| PorterChain SSO bridge routes
|--------------------------------------------------------------------------
|
| Mounted under /int/v1/porterchain. Unauthenticated by design — the
| PorterChain-signed SSO JWT is the credential (see SSO.md).
|
*/

Route::post('sso/exchange', [SsoController::class, 'exchange'])->name('porterchain.sso.exchange');
Route::post('sso/users/{uuid}/permissions', [SsoController::class, 'syncPermissions'])->name('porterchain.sso.sync-permissions');
