<?php

/**
 * Autoload + boot PorterChain Fleetbase bridge without Composer package discovery.
 * Required by the mounted RouteServiceProvider in Docker.
 */

$root = dirname(__DIR__);

spl_autoload_register(static function (string $class) use ($root): void {
    $prefix = 'Porterchain\\FleetbaseBridge\\';
    if (! str_starts_with($class, $prefix)) {
        return;
    }
    $relative = str_replace('\\', '/', substr($class, strlen($prefix)));
    $file = $root . '/src/' . $relative . '.php';
    if (is_file($file)) {
        require_once $file;
    }
});

use Porterchain\FleetbaseBridge\Providers\PorterchainBridgeServiceProvider;

if (function_exists('app')) {
    $app = app();
    if (! $app->providerIsLoaded(PorterchainBridgeServiceProvider::class)) {
        $app->register(PorterchainBridgeServiceProvider::class);
    }
}
