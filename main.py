
from algebra import ParseError, process_string


def main() -> None:
    print("DeMorganizer Program")
    while True:
        user_input = input(
            "Input boolean algebra to process via DeMorgan's Rules (input QUIT to exit): "
        ).strip()
        if user_input.lower() in {"quit", "exit"}:
            break
        if not user_input:
            continue
        try:
            print(process_string(user_input))
        except ParseError as err:
            print(f"Parse error: {err}")


if __name__ == "__main__":
    main()
