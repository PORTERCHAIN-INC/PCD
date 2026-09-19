<?php

namespace Porterchain\FleetbaseBridge\Providers;

use Illuminate\Support\Facades\Route;
use Illuminate\Support\ServiceProvider;

/**
 * Registers PorterChain SSO bridge routes under /int/v1/porterchain.
 * Does not modify upstream Fleetbase packages — mount this package via Docker.
 */
class PorterchainBridgeServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->mergeConfigFrom(
            dirname(__DIR__, 2) . '/config/porterchain-sso.php',
            'porterchain'
        );
    }

    public function boot(): void
    {
        Route::prefix('int/v1/porterchain')
            ->middleware('api')
            ->group(dirname(__DIR__, 2) . '/routes/sso.php');
    }
}
