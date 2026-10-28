(() => {
  'use strict';
  const today = document.getElementById('renewal-today');
  if (today) today.textContent = new Intl.DateTimeFormat('en-IN',{day:'numeric',month:'short',year:'numeric'}).format(new Date());
  // Global search is a real GET query, not a decorative input; the directory
  // restores its q parameter and filters the user's role-scoped records.
})();
