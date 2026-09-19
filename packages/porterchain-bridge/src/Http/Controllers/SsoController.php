<?php

namespace Porterchain\FleetbaseBridge\Http\Controllers;

use Fleetbase\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;
use Porterchain\FleetbaseBridge\Services\SsoBridgeService;
use RuntimeException;

/**
 * PorterChain SSO trust bridge endpoints (see PCD SSO.md).
 *
 * Unauthenticated by design — the PorterChain-signed SSO JWT is the credential.
 */
class SsoController extends Controller
{
    public function __construct(
        private readonly SsoBridgeService $bridge,
    ) {}

    /**
     * POST /int/v1/porterchain/sso/exchange
     *
     * Called server-to-server by the PorterChain API and by the Fleetbase
     * console /porterchain/sso route (token only).
     */
    public function exchange(Request $request): JsonResponse
    {
        $ssoToken = (string) ($request->input('sso_token') ?? $request->input('token') ?? '');

        if ($ssoToken === '') {
            return response()->json(['error' => 'sso_token_required'], 422);
        }

        try {
            $claims = $this->bridge->validateToken($ssoToken);
            $user = $this->bridge->provisionUser(
                $claims,
                $request->input('email'),
                $request->input('company_uuid')
            );
            $rolesAssigned = $this->bridge->syncAccess(
                $user,
                (array) $request->input('fleetbase_roles', []),
                (array) $request->input('fleetbase_permissions', []),
                $claims
            );
        } catch (RuntimeException $e) {
            return response()->json(['error' => $e->getMessage()], 401);
        }

        $token = $this->bridge->issueSessionToken($user);

        return response()->json([
            'fleetbase_user_uuid' => $user->uuid,
            'sanctum_token' => $token,
            // console route consumes `token` for session.manuallyAuthenticate()
            'token' => $token,
            'roles_assigned' => $rolesAssigned,
        ]);
    }

    /**
     * POST /int/v1/porterchain/sso/users/{uuid}/permissions
     */
    public function syncPermissions(Request $request, string $uuid): JsonResponse
    {
        $user = User::where('uuid', $uuid)->whereNull('deleted_at')->first();

        if (! $user instanceof User) {
            return response()->json(['error' => 'user_not_found'], 404);
        }

        $rolesAssigned = $this->bridge->syncAccess(
            $user,
            (array) $request->input('roles', []),
            (array) $request->input('permissions', [])
        );

        return response()->json([
            'fleetbase_user_uuid' => $user->uuid,
            'roles_assigned' => $rolesAssigned,
            'synced_at' => now()->toIso8601String(),
        ]);
    }
}
