class ARNFormatError(Exception):
    def __init__(self, m):
        self.message = m

    def __str__(self):
        return self.message


class CloudWatchLogException(Exception):
    def __init__(self, m):
        self.message = m

    def __str__(self):
        return self.message
