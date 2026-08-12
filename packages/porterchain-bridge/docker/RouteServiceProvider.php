<?php

namespace App\Providers;

use Illuminate\Foundation\Support\Providers\RouteServiceProvider as ServiceProvider;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

/**
 * Fleetbase RouteServiceProvider overlay (PorterChain).
 * Keeps upstream /health and mounts packages/porterchain-bridge SSO routes.
 */
class RouteServiceProvider extends ServiceProvider
{
    public function boot()
    {
        $bridgeRoot = base_path('packages/porterchain-bridge');
        if (is_dir($bridgeRoot)) {
            $this->bootPorterchainBridge($bridgeRoot);
        }

        $this->routes(
            function () {
                Route::get(
                    '/health',
                    function (Request $request) {
                        return response()->json(
                            [
                                'status' => 'ok',
                                'time' => microtime(true) - $request->attributes->get('request_start_time'),
                            ]
                        );
                    }
                );
            }
        );
    }

    private function bootPorterchainBridge(string $bridgeRoot): void
    {
        // Explicit requires — no Composer package discovery needed in the digest image.
        require_once $bridgeRoot . '/src/Services/SsoBridgeService.php';
        require_once $bridgeRoot . '/src/Http/Controllers/SsoController.php';

        $config = require $bridgeRoot . '/config/porterchain-sso.php';
        config(['porterchain' => array_replace_recursive((array) config('porterchain', []), $config)]);

        Route::prefix('int/v1/porterchain')
            ->middleware('api')
            ->group($bridgeRoot . '/routes/sso.php');
    }
}
