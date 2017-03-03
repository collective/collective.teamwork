/* JavaScript for membership management page for collective.teamwork */
/*jshint browser: true, nomen: false, eqnull: true, es5:true, trailing:true */

(function ($) {

    "use strict";

    // hookup overlays:
    function hookupOverlays() {
        // add existing user overlay:
        $('a.add-user-entry').prepOverlay({
            subtype: 'ajax',
            filter: 'div.page_section.existing_users',
            formselector: 'div.existing_users form.user_search'
        });
        // register new user overlay:
        $('a.register-user-entry').prepOverlay({
            subtype: 'ajax',
            filter: 'div.page_section.register_user'
        });
        // user info overlay:
        $('td.userinfo a.userinfo').prepOverlay({
            subtype: 'ajax',
            filter: '#content'
        });
        // user purge overlay:
        $('td.gridcell a.purge').prepOverlay({
            subtype: 'ajax',
            filter: '#content',
            formselector: '#content form.user-purge-form',
            closeselector: '#content form.user-purge-form input.cancelbutton',
            noform: 'reload',
            config: {
                onClose: function(e) {
                    var input = $('#content .user-purge-form .cancelbutton');
                    if (input.val() == 'Ok') {
                        /* on success (not cancel): reload after either
                           GET, POST, idea via http://goo.gl/Lrc4j 
                         */
                        window.location.href = window.location.pathname +
                            window.location.search;
                    }
                }
            }
        });
        // password reset overlay:
        $('a.password-reset').prepOverlay({
            subtype: 'ajax',
            filter: '#content form',
            formselector: 'form[name="mail_password"]',
            noform: function(e) {
               alert('User will be sent password reset email shortly.');
               return 'close';
            }
        });
        // roster view overlay for membership tab:
        $('a.view-roster').prepOverlay({
            subtype: 'ajax',
            filter: '#content',
            config: {
                onLoad: function(e) {
                    $('div.pb-ajax a.userinfo').prepOverlay({
                        subtype: 'ajax', filter: '#content',
                        config: {
                            onBeforeLoad: function(e) {
                                $('div.overlay').data('overlay').close();
                            }
                        }
                    });
                }
             }
        });
    }

    // modified grid table cell/row highlighting cues:
    function hookupGridModifiedHighlighting() {
        $('table.listing td input').click(function(event) {
            $(this).parent().addClass('modified');
            $(this).parent().parent().addClass('modified');
        });
    }

    // For all cells, hookup unlock button in viewers column checkbox:
    function hookupUnlockViewers() {
        $('table.listing td a.unlock').click(function(event) {
            $(this).parent().children('input.locked').show();
            $(this).parent().children('a.purge').show().addClass('block');
            $(this).parent()
                .children('a.password-reset')
                .show()
                .addClass('block');
            $(this).parent().children('.checkmark').hide();
            $(this).hide();
        });
    }

    $(document).ready(function () {
        hookupOverlays();
        hookupGridModifiedHighlighting();
        hookupUnlockViewers();

    });

}(jQuery));
