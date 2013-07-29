/* JavaScript for membership management page for collective.groupspaces */

jQuery(document).ready(function() {
    /* overlays */
    jQuery('a.add-user-entry').prepOverlay({
         subtype: 'ajax',
         filter: 'div.page_section.existing_users',
         formselector: 'div.existing_users form.user_search',
        });
    jQuery('a.register-user-entry').prepOverlay({
         subtype: 'ajax',
         filter: 'div.page_section.register_user',
        });
    jQuery('td.userinfo a.userinfo').prepOverlay({
         subtype: 'ajax',
         filter: '#content',
        });
    jQuery('td.gridcell a.purge').prepOverlay({
         subtype: 'ajax',
         filter: '#content',
         formselector: '#content form.user-purge-form',
         closeselector: '#content form.user-purge-form input.cancelbutton',
         noform: 'reload',
         config: {
            onClose: function(e) {
                var input = jQuery('#content form.user-purge-form input.cancelbutton');
                if (input.val() == 'Ok') {
                    /* on success (not cancel): reload after either GET, POST, idea via http://goo.gl/Lrc4j */
                    window.location.href = window.location.pathname + window.location.search;
                }
            }
         }
        });
    jQuery('a.password-reset').prepOverlay({
         subtype: 'ajax',
         filter: '#content form',
         formselector: 'form[name="mail_password"]',
         noform: function(e) { alert('User will be sent password reset email shortly.'); return 'close'; }
        });
    jQuery('a.view-roster').prepOverlay({
         subtype: 'ajax',
         filter: '#content',
         config: {
            onLoad: function(e) {
                jQuery('div.pb-ajax a.userinfo').prepOverlay({
                    subtype: 'ajax', filter: '#content',
                    config: { onBeforeLoad: function(e) { jQuery('div.overlay').data('overlay').close(); } }
                    });
            }
         }
        });

    /* modified grid table cell/row highlighting cues */
    jQuery('table.listing td input').click(function(event) {
        jQuery(this).parent().addClass('modified');
        jQuery(this).parent().parent().addClass('modified');
    });

    /* unlock viewers checkbox */
    jQuery('table.listing td a.unlock').click(function(event) {
        jQuery(this).parent().children('input.locked').show();
        jQuery(this).parent().children('a.purge').show().addClass('block');
        jQuery(this).parent().children('a.password-reset').show().addClass('block');
        jQuery(this).parent().children('.checkmark').hide();
        jQuery(this).hide();
    });

});
