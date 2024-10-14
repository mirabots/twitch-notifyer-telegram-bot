import sys

import uvicorn

from app.common.utils import get_args, get_logger, levelDEBUG, levelINFO

if __name__ == "__main__":
    args = get_args()
    logger = get_logger(levelDEBUG if args.env == "dev" else levelINFO)
    logger.info(f"{args.env} running {args.host}:{args.port}")

    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"][
        "fmt"
    ] = "%(levelprefix)s\t%(asctime)s\t\t%(message)s"
    log_config["formatters"]["access"][
        "fmt"
    ] = "REQUEST \t%(asctime)s \tfrom %(client_addr)s \t%(status_code)s '%(request_line)s'"

    try:
        uvicorn.run(
            "app.app:app",
            host=args.host,
            port=args.port,
            proxy_headers=True,
            log_config=log_config,
            use_colors=True,
            # reload=(True if args.env == "dev" else False),
            reload=False,
        )
    except KeyboardInterrupt:
        logger.info("KEYBOARD INTERRUPT")
        sys.exit(1)
