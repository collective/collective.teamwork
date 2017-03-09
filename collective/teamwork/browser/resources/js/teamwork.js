/*jshint browser: true, nomen: false, eqnull: true, es5:true, trailing:true */


(function ($) {
  $(document).ready(function () {
    var detect = [
          'body.portaltype-collective-teamwork-project',
          'body.portaltype-collective-teamwork-team',
          'body.portaltype-collective-teamwork-workspace',
        ].join(', ');
    if ($(detect).length || $('.home_icons a').length === 3) {
      // matching body, we are in the context of a workspace...
      $('#edit-zone #contentview-local_roles a span:last-child').text('Workgroup membership & sharing');
    }
    console.log('collective.teamwork ready');
  });
}(jQuery));
