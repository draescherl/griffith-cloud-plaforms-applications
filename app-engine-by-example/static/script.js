'use strict'
window.addEventListener('load', () => {
    document.querySelector('#sign-out').onclick = (() => {
        // Ask firebase to sign out the user
        firebase.auth().signOut();
    });

    const uiConfig = {
        signInSuccessUrl: '/',
        signInOptions: [
            firebase.auth.EmailAuthProvider.PROVIDER_ID
        ]
    };

    firebase.auth().onAuthStateChanged((user) => {
        if (user) {
            document.querySelector('#sign-out').hidden = false;
            document.querySelector('#login-info').hidden = false;

            console.log(`Signed in as ${user.displayName} (${user.email})`);

            user.getIdToken().then((token) => {
                document.cookie = "token=" + token;
            });
        } else {
            let ui = new firebaseui.auth.AuthUI(firebase.auth());
            ui.start('#firebase-auth-container', uiConfig);
            document.querySelector('#sign-out').hidden = true;
            document.querySelector('#login-info').hidden = true;
            document.cookie = "token=";
        }
    }, (error) => {
        console.log(error);
        alert('Unable to log in: ' + error);
    });
});