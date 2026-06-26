#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <netinet/ip.h>

int		count, max_fd, ids[65536];
char	*msgs[65536], buf[1001], out[64];
fd_set	afds, rfds, wfds;

int	extract_message(char **buf, char **msg)
{
	char	*nl, *n;

	*msg = 0;
	if (!*buf || !(nl = strstr(*buf, "\n")))
		return (0);
	n = calloc(strlen(nl + 1) + 1, 1);
	if (!n)
		return (-1);
	strcpy(n, nl + 1);
	*msg = *buf;
	*(nl + 1) = 0;
	*buf = n;
	return (1);
}

char	*str_join(char *buf, char *add)
{
	int		len = buf ? strlen(buf) : 0;
	char	*n = malloc(len + strlen(add) + 1);

	if (!n)
		return (0);
	n[0] = 0;
	if (buf)
		strcat(n, buf);
	free(buf);
	return (strcat(n, add));
}

void	die(void)
{
	write(2, "Fatal error\n", 12);
	exit(1);
}

void	send_all(int skip, char *s)
{
	for (int fd = 0; fd <= max_fd; fd++)
		if (fd != skip && FD_ISSET(fd, &wfds))
			send(fd, s, strlen(s), MSG_NOSIGNAL);
}

int	main(int ac, char **av)
{
	if (ac != 2)
	{
		write(2, "Wrong number of arguments\n", 26);
		exit(1);
	}

	int sock = socket(AF_INET, SOCK_STREAM, 0);
	if (sock < 0) die();
	FD_ZERO(&afds);
	max_fd = sock;
	FD_SET(sock, &afds);

	struct sockaddr_in sa = {.sin_family = AF_INET,
		.sin_port = htons(atoi(av[1])), .sin_addr.s_addr = htonl(2130706433)};
	if (bind(sock, (struct sockaddr *)&sa, sizeof(sa)) || listen(sock, 128))
		die();

	while (1)
	{
		rfds = wfds = afds;
		if (select(max_fd + 1, &rfds, &wfds, NULL, NULL) < 0)
			die();
		for (int fd = 0; fd <= max_fd; fd++)
		{
			if (!FD_ISSET(fd, &rfds))
				continue;
			if (fd == sock)
			{
				int cfd = accept(sock, NULL, NULL);
				if (cfd < 0) continue;
				max_fd = cfd > max_fd ? cfd : max_fd;
				ids[cfd] = count++;
				msgs[cfd] = NULL;
				FD_SET(cfd, &afds);
				sprintf(out, "server: client %d just arrived\n", ids[cfd]);
				send_all(cfd, out);
				break;
			}
			int n = recv(fd, buf, 1000, 0);
			if (n <= 0)
			{
				sprintf(out, "server: client %d just left\n", ids[fd]);
				send_all(fd, out);
				free(msgs[fd]);
				FD_CLR(fd, &afds);
				close(fd);
				break;
			}
			buf[n] = 0;
			if (!(msgs[fd] = str_join(msgs[fd], buf)))
				die();
			char *msg;
			while (extract_message(&msgs[fd], &msg))
			{
				sprintf(out, "client %d: ", ids[fd]);
				send_all(fd, out);
				send_all(fd, msg);
				free(msg);
			}
		}
	}
	return (0);
}