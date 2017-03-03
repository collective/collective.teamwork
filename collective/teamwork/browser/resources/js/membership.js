/*jshint browser: true, nomen: false, eqnull: true, es5:true, trailing:true */

(function ($) {

  function hookupOverlays() {
    console.log('TODO: overlays');
  }

  function hookupGridModifiedHighlighting() {
    $('table.listing td input').click(function(event) {
      $(this).parent().addClass('modified');
      $(this).parent().parent().addClass('modified');
    });
  }

  function hookupUnlockViewers() {
    $('table.listing td a.unlock').click(function(event) {
      var unlock = $(this),
          cell = unlock.parent();
      // hide the display only checkmark:
      cell.children('.checkmark').hide();
      // in its place, show the actual checkbox:
      cell.children('input.locked').show();
      // if/as applicable show buttons for purge, password reset, if in DOM:
      cell.children('a.purge, a.password-reset').show().addClass('block');
      // Hide the unlock button:
      unlock.hide();
    });
  }

  function initMembership() {
    hookupOverlays();
    hookupGridModifiedHighlighting();
    hookupUnlockViewers();
  }

  $(document).ready(initMembership);

}(jQuery));
