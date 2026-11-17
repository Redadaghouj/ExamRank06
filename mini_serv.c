#include <errno.h>
#include <string.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <netdb.h>
#include <sys/socket.h>
#include <netinet/in.h>

int		ids[65536], count, maxfd;
char	*msgs[65536], buf[1001], out[64];
fd_set	afds, rfds, wfds;

int extract_message(char **buf, char **msg)
{
	char	*newbuf;
	int	i;

	*msg = 0;
	if (*buf == 0)
		return (0);
	i = 0;
	while ((*buf)[i])
	{
		if ((*buf)[i] == '\n')
		{
			newbuf = calloc(1, sizeof(*newbuf) * (strlen(*buf + i + 1) + 1));
			if (newbuf == 0)
				return (-1);
			strcpy(newbuf, *buf + i + 1);
			*msg = *buf;
			(*msg)[i + 1] = 0;
			*buf = newbuf;
			return (1);
		}
		i++;
	}
	return (0);
}

char *str_join(char *buf, char *add)
{
	char	*newbuf;
	int		len;

	if (buf == 0)
		len = 0;
	else
		len = strlen(buf);
	newbuf = malloc(sizeof(*newbuf) * (len + strlen(add) + 1));
	if (newbuf == 0)
		return (0);
	newbuf[0] = 0;
	if (buf != 0)
		strcat(newbuf, buf);
	free(buf);
	strcat(newbuf, add);
	return (newbuf);
}

void	die(void)
{
	write(2, "Fatal error\n", 12);
	exit(1);
}

void	send_all(int from, char *s)
{
	for (int fd = 0; fd <= maxfd; fd++)
		if (fd != from && FD_ISSET(fd, &wfds))
			send(fd, s, strlen(s), 0);
}

int main(int ac, char **av)
{
	int sockfd, cfd, n, r;
	char *msg;
	struct sockaddr_in servaddr;

	if (ac != 2)
	{
		write(2, "Wrong number of arguments\n", 26);
		exit(1);
	}
	sockfd = socket(AF_INET, SOCK_STREAM, 0);
	bzero(&servaddr, sizeof(servaddr));
	servaddr.sin_family = AF_INET;
	servaddr.sin_addr.s_addr = htonl(2130706433); //127.0.0.1
	servaddr.sin_port = htons(atoi(av[1]));
	if (sockfd < 0 || bind(sockfd, (const struct sockaddr *)&servaddr, sizeof(servaddr)) || listen(sockfd, 128))
		die();
	FD_SET(sockfd, &afds);
	maxfd = sockfd;
	while (1)
	{
		rfds = wfds = afds;
		if (select(maxfd + 1, &rfds, &wfds, 0, 0) < 0)
			die();
		for (int fd = 0; fd <= maxfd; fd++)
		{
			if (!FD_ISSET(fd, &rfds))
				continue ;
			if (fd == sockfd)
			{
				if ((cfd = accept(sockfd, 0, 0)) < 0)
					break ;
				maxfd = cfd > maxfd ? cfd : maxfd;
				ids[cfd] = count++;
				msgs[cfd] = 0;
				FD_SET(cfd, &afds);
				sprintf(out, "server: client %d just arrived\n", ids[cfd]);
				send_all(cfd, out);
				break ;
			}
			if ((n = recv(fd, buf, 1000, 0)) <= 0)
			{
				sprintf(out, "server: client %d just left\n", ids[fd]);
				send_all(fd, out);
				free(msgs[fd]);
				FD_CLR(fd, &afds);
				close(fd);
				break ;
			}
			buf[n] = 0;
			if (!(msgs[fd] = str_join(msgs[fd], buf)))
				die();
			while ((r = extract_message(&msgs[fd], &msg)) == 1)
			{
				sprintf(out, "client %d: ", ids[fd]);
				send_all(fd, out);
				send_all(fd, msg);
				free(msg);
			}
			if (r < 0)
				die();
		}
	}
}