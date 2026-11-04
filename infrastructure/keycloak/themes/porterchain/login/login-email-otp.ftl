<#-- Porterchain override of the email-otp-authenticator form (for-keycloak, Unlicense).
     Shown only on a new/unrecognised browser. A successful code always remembers this browser
     (trust-device=true, per user+realm cookie), so the user is not asked again on it. -->
<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('email-otp'); section>
    <#if section = "header">
    <#elseif section = "form">
        <form id="kc-otp-login-form" class="${properties.kcFormClass!}" onsubmit="login.disabled = true; return true;" action="${url.loginAction}" method="post">
            <div class="${properties.kcFormGroupClass!}">
                <label for="email-otp" class="${properties.kcLabelClass!}">${msg("loginEmailOtp")}</label>
                <input id="email-otp" name="email-otp" class="${properties.kcInputClass!} pc-code-input" autocomplete="one-time-code"
                       inputmode="numeric" pattern="[0-9]*" maxlength="6" type="text" autofocus
                       aria-invalid="<#if messagesPerField.existsError('email-otp')>true</#if>" dir="ltr" />
                <#if messagesPerField.existsError('email-otp')>
                    <span id="input-error-email-otp-code" class="${properties.kcInputErrorMessageClass!}" aria-live="polite">${kcSanitize(messagesPerField.get('email-otp'))?no_esc}</span>
                </#if>
            </div>
            <#if deviceTrustEnabled?? && deviceTrustEnabled><input type="hidden" name="trust-device" value="true" /></#if>
            <div class="${properties.kcFormGroupClass!}">
                <button class="${properties.kcButtonClass!} ${properties.kcButtonPrimaryClass!} ${properties.kcButtonBlockClass!}" name="login" id="kc-login" type="submit">${msg("doContinue")}</button>
            </div>
            <p class="pc-resend">${msg("pcCodeNoEmail")}
                <button class="pc-link-btn" name="resend-email" id="kc-resend-email" type="submit" formnovalidate>${msg("doResendEmail")}</button>
            </p>
            <p class="pc-resend"><a href="${url.loginRestartFlowUrl}">${msg("pcCodeUseAnother")}</a></p>
        </form>
    </#if>
</@layout.registrationLayout>
