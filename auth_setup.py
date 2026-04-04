import msal

CLIENT_ID = "REMOVED"
AUTHORITY = "https://login.microsoftonline.com/consumers"
SCOPES = ["Tasks.ReadWrite"]

# Create a cache to save your login data
cache = msal.SerializableTokenCache()
app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)

print("Starting Microsoft Authentication...")
print("Opening browser on port 8080...")

# This forces the library to use the exact port we just whitelisted in Azure
result = app.acquire_token_interactive(scopes=SCOPES, port=8080)

if "access_token" in result:
    # Save the token to a file so our web server can use it later
    with open("token_cache.bin", "w") as f:
        f.write(cache.serialize())
    print("\n✅ SUCCESS! Login complete and token saved to token_cache.bin.")
    print("You never need to run this script again. You can now start app.py!")
else:
    print("\n❌ Error:", result.get("error"))
    print("Description:", result.get("error_description"))