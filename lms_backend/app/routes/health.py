from flask_smorest import Blueprint
from flask.views import MethodView

blp = Blueprint(
    "Health",
    "health",
    url_prefix="/",
    description="Health check and service info"
)

# PUBLIC_INTERFACE
@blp.route("/")
class HealthCheck(MethodView):
    """Health check endpoint.

    Returns a simple JSON confirming service is running.
    """
    def get(self):
        """
        Get service health
        ---
        get:
          summary: Health check
          description: Returns a simple healthy message.
          tags:
            - Health
          responses:
            200:
              description: Service is healthy
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      message:
                        type: string
        """
        return {"message": "Healthy"}
