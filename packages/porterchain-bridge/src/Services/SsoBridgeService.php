<?php

namespace Porterchain\FleetbaseBridge\Services;

use Firebase\JWT\JWT;
use Firebase\JWT\Key;
use Fleetbase\Models\Company;
use Fleetbase\Models\Role;
use Fleetbase\Models\User;
use Illuminate\Support\Carbon;
use Illuminate\Support\Str;
use RuntimeException;

/**
 * Validates PorterChain-signed HS256 SSO JWTs (SSO.md), provisions the matching
 * Fleetbase console user without a password, syncs role/permissions, and issues
 * a Sanctum session token.
 */
class SsoBridgeService
{
    /** PorterChain roles that map to Fleetbase's full-access Administrator role. */
    private const ADMIN_ROLES = ['super_admin', 'admin'];

    /**
     * @return object decoded JWT claims
     */
    public function validateToken(string $ssoToken): object
    {
        $secret = (string) config('porterchain.sso.jwt_secret');

        if ($secret === '') {
            throw new RuntimeException('sso_not_configured');
        }

        try {
            $claims = JWT::decode($ssoToken, new Key($secret, 'HS256'));
        } catch (\Firebase\JWT\ExpiredException $e) {
            throw new RuntimeException('sso_token_expired', 0, $e);
        } catch (\Throwable $e) {
            throw new RuntimeException('sso_token_invalid', 0, $e);
        }

        if (($claims->iss ?? null) !== config('porterchain.sso.issuer')) {
            throw new RuntimeException('sso_issuer_mismatch');
        }

        if (($claims->aud ?? null) !== config('porterchain.sso.audience')) {
            throw new RuntimeException('sso_audience_mismatch');
        }

        return $claims;
    }

    /**
     * Find or create the Fleetbase user for a PorterChain staff subject.
     * Users are provisioned without passwords — SSO is the only way in.
     */
    public function provisionUser(object $claims, ?string $email, ?string $companyUuid): User
    {
        $email = strtolower((string) ($email ?? $claims->email ?? ''));

        if ($email === '') {
            throw new RuntimeException('sso_email_required');
        }

        $company = $this->resolveCompany($companyUuid);
        $user = User::where('email', $email)->whereNull('deleted_at')->first();

        if (! $user instanceof User) {
            $user = User::create([
                'uuid' => (string) Str::uuid(),
                'company_uuid' => $company->uuid,
                'email' => $email,
                'name' => $this->nameFromEmail($email),
                'username' => $email,
                'status' => 'active',
                'email_verified_at' => Carbon::now(),
                'type' => 'user',
                'meta' => [
                    'porterchain_subject' => $claims->auth_subject ?? $claims->clerk_user_id ?? null,
                    'provisioned_via' => 'porterchain_sso',
                ],
            ]);
            $user->setUserType('user');
        }

        if (! $user->companies()->where('companies.uuid', $company->uuid)->exists()) {
            $company->addUser($user, $this->mapRole($claims));
        } else {
            $user->setCompany($company);
        }

        return $user;
    }

    /**
     * @param  array<int, string>  $fleetbaseRoles
     * @param  array<int, string>  $fleetbasePermissions
     * @return array<int, string>
     */
    public function syncAccess(User $user, array $fleetbaseRoles, array $fleetbasePermissions, ?object $claims = null): array
    {
        $roleName = $this->mapRole($claims, $fleetbaseRoles, $fleetbasePermissions);
        $role = Role::findOrCreate($roleName, 'sanctum');

        $assigned = [];
        try {
            $user->assignSingleRole($role);
            $assigned[] = $role->name;
        } catch (\Throwable $e) {
            report($e);
        }

        return $assigned;
    }

    public function issueSessionToken(User $user): string
    {
        $user->updateLastLogin();

        return $user->createToken($user->uuid)->plainTextToken;
    }

    private function resolveCompany(?string $companyUuid): Company
    {
        $uuid = $companyUuid ?: config('porterchain.fleetbase.default_company_uuid');

        $company = $uuid
            ? Company::where('uuid', $uuid)->first()
            : Company::orderBy('created_at')->first();

        if (! $company instanceof Company) {
            throw new RuntimeException('sso_company_not_found');
        }

        return $company;
    }

    /**
     * @param  array<int, string>  $roles
     * @param  array<int, string>  $permissions
     */
    private function mapRole(?object $claims = null, array $roles = [], array $permissions = []): string
    {
        $roles = $roles ?: (array) ($claims->roles ?? []);
        $permissions = $permissions ?: (array) ($claims->permissions ?? []);

        if (in_array('*', $permissions, true) || array_intersect(self::ADMIN_ROLES, $roles)) {
            return 'Administrator';
        }

        return $roles[0] ?? 'Staff';
    }

    private function nameFromEmail(string $email): string
    {
        $local = Str::of($email)->before('@')->replace(['.', '_', '-'], ' ')->title();

        return (string) ($local->isEmpty() ? $email : $local);
    }
}
