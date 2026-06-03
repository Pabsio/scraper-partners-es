exports.handler = async (event) => {
  const body = JSON.parse(event.body);
  const email = body?.user?.email || "";

  if (!email.endsWith("@holidaypirates.com")) {
    return {
      statusCode: 200,
      body: JSON.stringify({
        app_metadata: {},
        error: "Access restricted to @holidaypirates.com accounts."
      })
    };
  }

  return {
    statusCode: 200,
    body: JSON.stringify({ app_metadata: {} })
  };
};
